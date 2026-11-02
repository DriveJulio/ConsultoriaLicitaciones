"""Acceso a Claude.

Tres niveles:
- Lectores (Haiku 5.5, esfuerzo bajo): leen material crudo y devuelven un extracto fiel.
- Analistas (Opus 5.5, esfuerzo medio): analizan los extractos y producen conclusiones.
- Orquestadores (Fable 5.1): ver agents/orquestador.py.
"""
from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any

from . import config
from .agents.prompts import SYSTEM_ANALISTA, SYSTEM_LECTOR


class RechazoModelo(RuntimeError):
    """El modelo (y su fallback) rechazó la consulta."""


@lru_cache(maxsize=1)
def client():
    import anthropic

    return anthropic.Anthropic()


def texto(resp) -> str:
    return "".join(getattr(b, "text", "") for b in resp.content if b.type == "text").strip()


# --- Contabilidad de tokens por modelo (para medir el ahorro) -----------------
_uso_lock = threading.Lock()
USO: dict[str, dict[str, int]] = {}


def _contar(resp) -> None:
    u = getattr(resp, "usage", None)
    if u is None:
        return
    with _uso_lock:
        m = USO.setdefault(getattr(resp, "model", "?"), {"llamadas": 0, "entrada": 0, "salida": 0, "cache": 0})
        m["llamadas"] += 1
        m["entrada"] += (getattr(u, "input_tokens", 0) or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
        m["cache"] += getattr(u, "cache_read_input_tokens", 0) or 0
        m["salida"] += getattr(u, "output_tokens", 0) or 0


# --- Lector (Haiku 5.5) --------------------------------------------------------
# Material crudo leído en esta ejecución, para preguntas de seguimiento y ver_fragmento.
FUENTES: dict[str, list[str]] = {}


def _registrar_fuente(material: str) -> str:
    import hashlib

    fid = "f_" + hashlib.sha1(material.encode("utf-8")).hexdigest()[:8]
    FUENTES.setdefault(fid, material.splitlines())
    return fid


def _numerar(lineas: list[str], desde: int) -> str:
    return "\n".join(f"L{desde + i}| {l}" for i, l in enumerate(lineas))


def _bloques_numerados(fid: str) -> list[str]:
    """Bloques del material con número de línea, para que Haiku cite la ubicación exacta."""
    lineas, bloques, actual, tam, inicio = FUENTES[fid], [], [], 0, 1
    for n, l in enumerate(lineas, 1):
        if actual and tam + len(l) > config.LECTOR_CHARS_POR_BLOQUE:
            bloques.append(_numerar(actual, inicio))
            actual, tam, inicio = [], 0, n
        actual.append(l)
        tam += len(l) + 8
    if actual:
        bloques.append(_numerar(actual, inicio))
    return bloques


def _haiku(instruccion: str, bloque: str) -> str:
    with client().messages.stream(
        model=config.LECTOR_MODEL,
        max_tokens=16000,
        system=[{"type": "text", "text": SYSTEM_LECTOR, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"{instruccion}\n<material>\n{bloque}\n</material>"}],
        output_config={"effort": config.LECTOR_EFFORT},
    ) as stream:
        resp = stream.get_final_message()
    _contar(resp)
    if resp.stop_reason == "refusal":
        # Haiku no tiene fallback del lado del servidor: el analista lee el crudo (recortado).
        return f"[SIN EXTRAER: el lector rechazó este bloque; texto original recortado]\n{bloque[:40000]}"
    return texto(resp)


def _en_paralelo(fn, items: list) -> list:
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(fn, items))


def lector(material: str, foco: str = "datos con valor legal, plazos y documentos") -> str:
    """Devuelve un extracto fiel del material, con id de fuente para preguntas de seguimiento.

    Si es corto, lo devuelve tal cual (resumirlo no ahorra)."""
    if len(material) <= config.LECTOR_UMBRAL_CHARS:
        return material
    fid = _registrar_fuente(material)
    bloques = _bloques_numerados(fid)
    instr = (f"<foco>{foco}</foco>\nIndicá entre corchetes las líneas de donde sale cada dato (ej. [L120-L124]).")
    extractos = _en_paralelo(lambda b: _haiku(instr, b), bloques)
    return (f"[fuente {fid} · {len(FUENTES[fid])} líneas · podés usar preguntar_al_lector / ver_fragmento]\n"
            + "\n\n".join(extractos))


def preguntar_al_lector(fuente: str, pregunta: str) -> str:
    """Opus le pregunta a Haiku algo puntual sobre una fuente ya leída. Respuesta con cita y líneas."""
    if fuente not in FUENTES:
        return f"ERROR: fuente desconocida {fuente}. Fuentes disponibles: {', '.join(FUENTES) or '(ninguna)'}"
    instr = (f"<pregunta>{pregunta}</pregunta>\nRespondé SOLO con lo que dice el material: cita textual entre "
             "comillas y líneas exactas [Lx-Ly]. Si en este material no está, respondé solamente: NO FIGURA.")
    respuestas = _en_paralelo(lambda b: _haiku(instr, b), _bloques_numerados(fuente))
    utiles = [r for r in respuestas if r.strip().upper() != "NO FIGURA"]
    return "\n\n".join(utiles) if utiles else "NO FIGURA en la fuente."


def ver_fragmento(fuente: str, desde: int, hasta: int) -> str:
    """Devuelve el texto ORIGINAL de esas líneas (máx. 300), para ir al lugar preciso."""
    if fuente not in FUENTES:
        return f"ERROR: fuente desconocida {fuente}"
    lineas = FUENTES[fuente]
    desde, hasta = max(1, desde), min(len(lineas), hasta, max(1, desde) + 299)
    return _numerar(lineas[desde - 1:hasta], desde)


def leer_url(url: str, foco: str) -> str:
    """Descarga una URL pública y la pasa por el lector."""
    from .monitors import web

    try:
        crudo = web.texto_visible(web.descargar(url, motivo="leer_url (analista)"))
    except Exception as e:
        return f"ERROR al leer {url}: {type(e).__name__}: {e}"
    return f"<extracto url=\"{url}\">\n{lector(crudo, foco)}\n</extracto>"


# --- Analista (Opus 5.5) -------------------------------------------------------
HERRAMIENTA_LEER_URL = {
    "name": "leer_url",
    "description": (
        "Lee una página o documento público (URL) y devuelve un extracto fiel preparado por un lector. "
        "Indicá en 'foco' qué datos necesitás. Es la forma de leer páginas: más barata y precisa."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {"url": {"type": "string"}, "foco": {"type": "string"}},
        "required": ["url", "foco"],
        "additionalProperties": False,
    },
}


HERRAMIENTAS_LECTOR = [
    {
        "name": "preguntar_al_lector",
        "description": (
            "Si tenés una duda sobre un extracto marcado [fuente f_xxx], preguntale al lector que leyó el original. "
            "Responde con cita textual y números de línea, o NO FIGURA."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"fuente": {"type": "string"}, "pregunta": {"type": "string"}},
            "required": ["fuente", "pregunta"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ver_fragmento",
        "description": "Lee el texto ORIGINAL de una fuente entre dos números de línea (máx. 300 líneas).",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"fuente": {"type": "string"}, "desde": {"type": "integer"}, "hasta": {"type": "integer"}},
            "required": ["fuente", "desde", "hasta"],
            "additionalProperties": False,
        },
    },
]

_HANDLERS = {
    "leer_url": lambda i: leer_url(i["url"], i["foco"]),
    "preguntar_al_lector": lambda i: preguntar_al_lector(i["fuente"], i["pregunta"]),
    "ver_fragmento": lambda i: ver_fragmento(i["fuente"], int(i["desde"]), int(i["hasta"])),
}


def _ejecutar_herramienta(bloque) -> dict:
    try:
        salida = _HANDLERS[bloque.name](dict(bloque.input))
    except Exception as e:
        salida = f"ERROR: {type(e).__name__}: {e}"
    r = {"type": "tool_result", "tool_use_id": bloque.id, "content": salida}
    if salida.startswith("ERROR"):
        r["is_error"] = True
    return r


def _web_search(dominios: list[str] | None) -> dict[str, Any]:
    search: dict[str, Any] = {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}
    if dominios:
        search["allowed_domains"] = dominios
    return search


def analista(
    tarea: str,
    contexto: str = "",
    usar_web: bool = False,
    dominios: list[str] | None = None,
    schema: dict | None = None,
    max_tokens: int = 32000,
    max_iteraciones: int = 12,
) -> str | dict:
    """Ejecuta una tarea con un analista Opus 5.5 (esfuerzo medio).

    - usar_web: habilita web_search (dominios oficiales) + leer_url (lectura vía Haiku).
    - schema: si se pasa, devuelve un dict validado por structured outputs.
    """
    kwargs: dict[str, Any] = {"tools": list(HERRAMIENTAS_LECTOR)}
    output_config: dict[str, Any] = {"effort": config.WORKER_EFFORT}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    if usar_web:
        dom = dominios if dominios is not None else config.DOMINIOS_OFICIALES
        kwargs["tools"] = [_web_search(dom), HERRAMIENTA_LEER_URL, *HERRAMIENTAS_LECTOR]

    contenido = f"{contexto}\n\n<tarea>\n{tarea}\n</tarea>" if contexto else f"<tarea>\n{tarea}\n</tarea>"
    messages: list[dict[str, Any]] = [{"role": "user", "content": contenido}]

    resp = None
    for _ in range(max_iteraciones):
        with client().beta.messages.stream(
            model=config.WORKER_MODEL,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": SYSTEM_ANALISTA, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            output_config=output_config,
            betas=[config.FALLBACK_BETA],
            fallbacks="default",
            **kwargs,
        ) as stream:
            resp = stream.get_final_message()
        _contar(resp)
        if resp.stop_reason == "pause_turn":  # la búsqueda web pausó el turno
            messages.append({"role": "assistant", "content": resp.content})
            continue
        usos = [b for b in resp.content if b.type == "tool_use" and b.name in _HANDLERS]
        if resp.stop_reason == "tool_use" and usos:
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": _en_paralelo(_ejecutar_herramienta, usos)})
            continue
        break

    if resp.stop_reason == "refusal":
        raise RechazoModelo(f"Analista rechazó la tarea: {getattr(resp, 'stop_details', None)}")
    salida = texto(resp)
    if schema:
        return json.loads(salida)
    return salida


def resumen_uso() -> str:
    if not USO:
        return ""
    filas = "\n".join(
        f"| {m} | {u['llamadas']} | {u['entrada']:,} | {u['cache']:,} | {u['salida']:,} |" for m, u in sorted(USO.items())
    )
    return ("\n\n## Uso de tokens\n\n| Modelo | Llamadas | Entrada | Caché (lectura) | Salida |\n"
            f"|---|---|---|---|---|\n{filas}\n")
