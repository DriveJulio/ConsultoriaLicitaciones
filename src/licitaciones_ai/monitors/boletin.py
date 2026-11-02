"""Monitor diario del Boletín Oficial de la República Argentina (primera sección).

Flujo:
1. Descarga el sumario de la primera sección del día y detecta avisos por palabras clave.
2. Un analista (Opus 5.5) clasifica cada aviso candidato: ¿modifica el régimen de contrataciones?
3. Si hay cambios relevantes, el Especialista (Fable 5.1) evalúa impacto y registra alertas.
4. Si la descarga directa falla, un analista revisa el BO con búsqueda web en dominios oficiales.
"""
from __future__ import annotations

from datetime import date

import yaml

from .. import config, llm, state
from . import web

BASE = "https://www.boletinoficial.gob.ar"
ESTADO = config.DATA_DIR / "boletin_estado.json"
NOVEDADES = config.KNOWLEDGE_DIR / "novedades_normativas.md"

SCHEMA_CLASIFICACION = {
    "type": "object",
    "properties": {
        "relevante": {"type": "boolean"},
        "tipo_cambio": {
            "type": "string",
            "enum": ["modifica_regimen", "nueva_norma", "montos_o_modulos", "procedimiento_onc", "otro", "ninguno"],
        },
        "norma": {"type": "string", "description": "Tipo y número de la norma publicada."},
        "normas_afectadas": {"type": "array", "items": {"type": "string"}},
        "resumen": {"type": "string"},
        "vigencia": {"type": "string", "description": "Desde cuándo rige, según el texto."},
        "impacto": {"type": "string", "enum": ["alto", "medio", "bajo", "nulo"]},
        "acciones": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["relevante", "tipo_cambio", "norma", "normas_afectadas", "resumen", "vigencia", "impacto", "acciones"],
    "additionalProperties": False,
}


def palabras_clave() -> list[str]:
    cfg = yaml.safe_load((config.CONFIG_DIR / "normativa.yaml").read_text(encoding="utf-8"))
    return [k.lower() for k in cfg.get("palabras_clave_boletin", [])]


def url_seccion(dia: date) -> str:
    return f"{BASE}/seccion/primera/{dia:%Y%m%d}"


def extraer_avisos(html: str, base: str = BASE) -> list[dict[str, str]]:
    """Devuelve los enlaces a avisos de la primera sección con su texto."""
    avisos = []
    for e in web.enlaces(html, base):
        if "/detalleAviso/primera/" in e["url"]:
            avisos.append(e)
    return avisos


def filtrar(avisos: list[dict[str, str]], claves: list[str]) -> list[dict[str, str]]:
    return [a for a in avisos if any(k in a["texto"].lower() for k in claves)]


def _clasificar(aviso: dict[str, str], cuerpo: str) -> dict:
    return llm.analista(
        "Clasificá este aviso del Boletín Oficial: ¿afecta el régimen de contrataciones públicas "
        "(compras, obra pública, PPP, concesiones, compre argentino, redeterminación de precios, "
        "procedimientos de la ONC, montos/módulos, integridad o ética pública aplicada a contrataciones)? "
        "Basate solo en el texto. Si no afecta, relevante=false e impacto='nulo'.",
        contexto=(
            f"<aviso url=\"{aviso['url']}\">\n<titulo>{aviso['texto']}</titulo>\n<extracto>\n"
            + llm.lector(cuerpo, "norma publicada, qué modifica/deroga/crea, artículos clave, vigencia, "
                                 "montos/módulos/plazos, organismo y alcance")
            + "\n</extracto>\n</aviso>"
        ),
        schema=SCHEMA_CLASIFICACION,
    )


def _revision_por_web(dia: date) -> str:
    return str(
        llm.analista(
            f"Revisá la primera sección del Boletín Oficial de la República Argentina del {dia:%d/%m/%Y} "
            f"({url_seccion(dia)}). Listá TODAS las normas publicadas ese día que afecten contrataciones "
            "públicas (régimen general, obra pública, PPP, compre argentino, ONC, montos/módulos, "
            "redeterminación de precios). Para cada una: norma, qué cambia, vigencia, URL del aviso. "
            "Si no hay ninguna, respondé exactamente 'SIN NOVEDADES'. Si no pudiste acceder, decilo.",
            usar_web=True,
        )
    )


def ejecutar(dia: date | None = None) -> str:
    dia = dia or config.ahora().date()
    estado = state.leer_json(ESTADO, {"procesados": []})
    procesados = set(estado["procesados"])

    relevantes: list[dict] = []
    fuente = "directa"
    try:
        html = web.descargar(url_seccion(dia))
        candidatos = [a for a in filtrar(extraer_avisos(html), palabras_clave()) if a["url"] not in procesados]
        for aviso in candidatos:
            cuerpo = web.texto_visible(web.descargar(aviso["url"]))
            clasif = _clasificar(aviso, cuerpo)
            procesados.add(aviso["url"])
            if clasif["relevante"] and clasif["impacto"] != "nulo":
                relevantes.append({**clasif, "url": aviso["url"], "titulo": aviso["texto"]})
        detalle_web = ""
    except Exception as e:  # sitio caído, HTML cambiado, bloqueo: plan B con búsqueda web
        fuente = f"web (descarga directa falló: {type(e).__name__})"
        detalle_web = _revision_por_web(dia)

    estado["procesados"] = sorted(procesados)[-2000:]
    estado["ultimo_chequeo"] = config.ahora().isoformat(timespec="minutes")
    state.escribir_json(ESTADO, estado)

    hay_novedades = bool(relevantes) or (detalle_web and "SIN NOVEDADES" not in detalle_web.upper())
    evaluacion = ""
    if hay_novedades:
        from ..agents.orquestador import dump, especialista

        material = dump(relevantes) if relevantes else detalle_web
        esp = especialista()
        evaluacion = esp.enviar(
            f"El monitor del Boletín Oficial del {dia:%d/%m/%Y} detectó posibles cambios normativos "
            f"(fuente: {fuente}).\n\n<novedades>\n{material}\n</novedades>\n\n"
            "1) Verificá con un analista (usar_web=true) cada cambio contra el texto oficial. "
            "2) Contrastalo con knowledge/marco_normativo.md: qué queda modificado, derogado o desactualizado. "
            "3) Revisá config/expedientes.yaml: ¿afecta algún proceso en curso? "
            "4) Registrá una alerta por cada cambio con impacto real y una propuesta si hay que actualizar "
            "el marco normativo. Respondé con un resumen ejecutivo."
        )
        with NOVEDADES.open("a", encoding="utf-8") as f:
            f.write(f"\n## {dia:%Y-%m-%d} — Boletín Oficial\n\n")
            for r in relevantes:
                f.write(f"- **{r['norma']}** ({r['impacto']}): {r['resumen']} — vigencia: {r['vigencia']} — {r['url']}\n")
            if detalle_web:
                f.write(f"{detalle_web}\n")

    reporte = (
        f"# Boletín Oficial — {dia:%Y-%m-%d}\n\nFuente: {fuente}\n\n"
        + (("## Evaluación del Especialista\n\n" + evaluacion) if evaluacion else "Sin novedades relevantes para contrataciones.")
    )
    return str(state.guardar_reporte("boletin", reporte))
