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
def _bloques(material: str, tam: int) -> list[str]:
    if len(material) <= tam:
        return [material]
    partes, i = [], 0
    while i < len(material):
        fin = min(i + tam, len(material))
        corte = material.rfind("\n", i + tam // 2, fin) if fin < len(material) else fin
        fin = corte if corte > i else fin
        partes.append(material[i:fin])
        i = fin
    return partes


def _leer_bloque(bloque: str, foco: str, n: int, total: int) -> str:
    parte = f" (parte {n} de {total})" if total > 1 else ""
    with client().messages.stream(
        model=config.LECTOR_MODEL,
        max_tokens=16000,
        system=[{"type": "text", "text": SYSTEM_LECTOR, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"<foco>{foco}</foco>\n<material{parte}>\n{bloque}\n</material>"}],
        output_config={"effort": config.LECTOR_EFFORT},
    ) as stream:
        resp = stream.get_final_message()
    _contar(resp)
    if resp.stop_reason == "refusal":
        # Haiku no tiene fallback del lado del servidor: el analista lee el crudo (recortado).
        return f"[SIN EXTRAER: el lector rechazó este bloque; texto original recortado]\n{bloque[:40000]}"
    return texto(resp)


def lector(material: str, foco: str = "datos con valor legal, plazos y documentos") -> str:
    """Devuelve un extracto fiel del material. Si es corto, lo devuelve tal cual (no ahorra leerlo)."""
    if len(material) <= config.LECTOR_UMBRAL_CHARS:
        return material
    bloques = _bloques(material, config.LECTOR_CHARS_POR_BLOQUE)
    with ThreadPoolExecutor(max_workers=4) as pool:
        extractos = list(pool.map(lambda nb: _leer_bloque(nb[1], foco, nb[0], len(bloques)), enumerate(bloques, 1)))
    return "\n\n".join(extractos)


def leer_url(url: str, foco: str) -> str:
    """Descarga una URL pública y la pasa por el lector."""
    from .monitors import web

    try:
        crudo = web.texto_visible(web.descargar(url))
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
    kwargs: dict[str, Any] = {}
    output_config: dict[str, Any] = {"effort": config.WORKER_EFFORT}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    if usar_web:
        dom = dominios if dominios is not None else config.DOMINIOS_OFICIALES
        kwargs["tools"] = [_web_search(dom), HERRAMIENTA_LEER_URL]

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
        usos = [b for b in resp.content if b.type == "tool_use" and b.name == "leer_url"]
        if resp.stop_reason == "tool_use" and usos:
            messages.append({"role": "assistant", "content": resp.content})
            with ThreadPoolExecutor(max_workers=4) as pool:
                salidas = list(pool.map(lambda b: leer_url(b.input["url"], b.input["foco"]), usos))
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": b.id, "content": s,
                 **({"is_error": True} if s.startswith("ERROR") else {})}
                for b, s in zip(usos, salidas)
            ]})
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
