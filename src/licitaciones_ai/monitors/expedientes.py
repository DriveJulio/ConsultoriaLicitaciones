"""Monitor de expedientes / procesos de contratación que la consultora sigue.

Corre 3 veces por día (09:00, 14:00 y 18:30 hora Argentina). Para cada proceso activo de
config/expedientes.yaml:
1. Descarga la página pública (COMPR.AR, CONTRAT.AR, portal provincial, etc.).
2. Compara con la última foto (texto + enlaces a documentos).
3. Si cambió, un analista (Opus 5.5) explica la novedad y calcula plazos.
4. Si la urgencia es alta, el Especialista (Fable 5.1) recomienda acción y genera alerta.
"""
from __future__ import annotations

import difflib
import re
from typing import Any

import yaml

from .. import config, llm, state
from . import web

DIR_ESTADO = config.DATA_DIR / "expedientes"
FALLAS_PARA_ALERTA = 3

SCHEMA_NOVEDAD = {
    "type": "object",
    "properties": {
        "hay_novedad_sustantiva": {"type": "boolean"},
        "etapa": {"type": "string", "description": "Etapa actual del proceso."},
        "resumen": {"type": "string"},
        "documentos_nuevos": {"type": "array", "items": {"type": "string"}},
        "plazos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "que": {"type": "string"},
                    "vence": {"type": "string"},
                    "fundamento": {"type": "string"},
                    "verificado": {"type": "boolean"},
                },
                "required": ["que", "vence", "fundamento", "verificado"],
                "additionalProperties": False,
            },
        },
        "urgencia": {"type": "string", "enum": ["alta", "media", "baja"]},
        "acciones": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["hay_novedad_sustantiva", "etapa", "resumen", "documentos_nuevos", "plazos", "urgencia", "acciones"],
    "additionalProperties": False,
}

# Ruido típico de portales (fechas/horas de render, contadores) que no es novedad real.
_RUIDO = re.compile(r"(\b\d{1,2}:\d{2}(:\d{2})?\b|ViewState|__EVENT\w+|visitas?:?\s*\d+)", re.IGNORECASE)


def cargar() -> list[dict[str, Any]]:
    cfg = yaml.safe_load((config.CONFIG_DIR / "expedientes.yaml").read_text(encoding="utf-8")) or {}
    return [e for e in cfg.get("expedientes", []) or [] if e.get("activo", True)]


def normalizar(texto: str) -> str:
    return "\n".join(_RUIDO.sub("", l).strip() for l in texto.splitlines() if _RUIDO.sub("", l).strip())


def diferencias(anterior: str, actual: str, max_lineas: int = 400) -> str:
    diff = difflib.unified_diff(anterior.splitlines(), actual.splitlines(), "anterior", "actual", lineterm="", n=1)
    return "\n".join(list(diff)[:max_lineas])


def foto(exp: dict) -> dict:
    html = web.descargar(exp["url"])
    texto = normalizar(web.texto_visible(html))
    links = [l for l in web.enlaces(html, exp["url"]) if l["texto"] or l["url"].lower().endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip"))]
    return {"texto": texto, "enlaces": links, "huella": web.huella(texto + "".join(sorted(l["url"] for l in links)))}


def _analizar(exp: dict, diff: str, nuevos_links: list[dict], texto: str) -> dict:
    return llm.analista(
        "Este proceso de contratación cambió desde el último control. Explicá qué novedad hay "
        "(acta de apertura, circular, dictamen de evaluación, adjudicación, impugnación, prórroga, etc.), "
        "en qué etapa está y qué plazos empiezan a correr (con fundamento normativo; verificado=false si no "
        "lo pudiste confirmar en el texto). Si el cambio es solo cosmético, hay_novedad_sustantiva=false.",
        contexto=(
            f"<proceso id=\"{exp['id']}\" organismo=\"{exp.get('organismo', '')}\" "
            f"plataforma=\"{exp.get('plataforma', '')}\" cliente=\"{exp.get('cliente', '')}\">\n"
            f"Nombre: {exp.get('nombre', '')}\nNotas internas: {exp.get('notas', '')}\n"
            f"Fecha y hora del control: {config.ahora():%Y-%m-%d %H:%M} (Argentina)\n</proceso>\n"
            f"<diff>\n{diff}\n</diff>\n<documentos_nuevos>\n{nuevos_links}\n</documentos_nuevos>\n"
            f"<pagina_actual>\n{texto[:120000]}\n</pagina_actual>"
        ),
        schema=SCHEMA_NOVEDAD,
    )


def _escalar(exp: dict, analisis: dict) -> str:
    from ..agents.orquestador import dump, especialista

    return especialista().enviar(
        f"Novedad de urgencia {analisis['urgencia']} en el proceso '{exp.get('nombre')}' ({exp['id']}, "
        f"{exp.get('organismo', '')}, cliente: {exp.get('cliente', '')}). URL: {exp['url']}\n\n"
        f"<analisis>\n{dump(analisis)}\n</analisis>\n\n"
        "Verificá los plazos (hábiles/corridos, desde cuándo se computan, norma aplicable al régimen del "
        "organismo) y recomendá la acción concreta para el cliente (observar, impugnar, presentar, pedir vista, "
        "mejorar oferta, no hacer nada). Registrá una alerta con el plazo y la acción."
    )


def ejecutar() -> str:
    lineas_reporte: list[str] = []
    for exp in cargar():
        path = DIR_ESTADO / f"{exp['id']}.json"
        previo = state.leer_json(path, {})
        try:
            actual = foto(exp)
        except Exception as e:
            fallas = previo.get("fallas", 0) + 1
            previo.update({"fallas": fallas, "ultimo_error": f"{type(e).__name__}: {e}"[:500]})
            state.escribir_json(path, previo)
            lineas_reporte.append(f"- ⚠️ **{exp['id']}**: no se pudo leer ({type(e).__name__}), falla #{fallas}")
            if fallas == FALLAS_PARA_ALERTA:
                state.registrar("alerta", f"No se puede leer el proceso {exp['id']}",
                                f"{FALLAS_PARA_ALERTA} fallas seguidas. URL: {exp['url']}. Error: {e}", "media", "monitor")
            continue

        ahora = config.ahora().isoformat(timespec="minutes")
        if not previo.get("huella"):
            state.escribir_json(path, {**actual, "fallas": 0, "ultimo_cambio": ahora, "ultimo_chequeo": ahora})
            lineas_reporte.append(f"- 🆕 **{exp['id']}**: primera foto guardada (línea de base).")
            continue

        if previo["huella"] == actual["huella"]:
            previo.update({"fallas": 0, "ultimo_chequeo": ahora})
            state.escribir_json(path, previo)
            lineas_reporte.append(f"- ✅ **{exp['id']}**: sin cambios.")
            continue

        urls_previas = {l["url"] for l in previo.get("enlaces", [])}
        nuevos = [l for l in actual["enlaces"] if l["url"] not in urls_previas]
        analisis = _analizar(exp, diferencias(previo.get("texto", ""), actual["texto"]), nuevos, actual["texto"])
        state.escribir_json(path, {**actual, "fallas": 0, "ultimo_cambio": ahora, "ultimo_chequeo": ahora,
                                   "ultimo_analisis": analisis})

        if not analisis["hay_novedad_sustantiva"]:
            lineas_reporte.append(f"- ✅ **{exp['id']}**: cambio cosmético, sin novedad.")
            continue

        linea = f"- 🔔 **{exp['id']}** [{analisis['urgencia']}] {analisis['etapa']}: {analisis['resumen']}"
        if analisis["urgencia"] == "alta":
            recomendacion = _escalar(exp, analisis)
            linea += f"\n\n  **Especialista:** {recomendacion}"
        else:
            plazos = "\n".join(f"  - {p['que']}: {p['vence']} ({p['fundamento']})" for p in analisis["plazos"])
            state.registrar("alerta", f"Novedad en {exp.get('nombre', exp['id'])}",
                            f"{analisis['resumen']}\n\nPlazos:\n{plazos or '  - (ninguno)'}\n\nURL: {exp['url']}",
                            analisis["urgencia"], "monitor")
        lineas_reporte.append(linea)

    cuerpo = "\n".join(lineas_reporte) or "_No hay expedientes activos en config/expedientes.yaml._"
    return str(state.guardar_reporte("expedientes", f"# Control de expedientes — {config.ahora():%Y-%m-%d %H:%M}\n\n{cuerpo}"))
