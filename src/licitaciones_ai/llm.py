"""Acceso a Claude: analistas (Opus 5.5, esfuerzo medio) y utilidades comunes."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from . import config
from .agents.prompts import SYSTEM_ANALISTA


class RechazoModelo(RuntimeError):
    """El modelo (y su fallback) rechazó la consulta."""


@lru_cache(maxsize=1)
def client():
    import anthropic

    return anthropic.Anthropic()


def texto(resp) -> str:
    return "".join(getattr(b, "text", "") for b in resp.content if b.type == "text").strip()


def _web_tools(dominios: list[str] | None) -> list[dict[str, Any]]:
    search: dict[str, Any] = {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}
    fetch: dict[str, Any] = {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 12}
    if dominios:
        search["allowed_domains"] = dominios
        fetch["allowed_domains"] = dominios
    return [search, fetch]


def analista(
    tarea: str,
    contexto: str = "",
    usar_web: bool = False,
    dominios: list[str] | None = None,
    schema: dict | None = None,
    max_tokens: int = 32000,
) -> str | dict:
    """Ejecuta una tarea con un analista Opus 5.5 (esfuerzo medio).

    - usar_web: habilita web_search/web_fetch (por defecto limitado a dominios oficiales).
    - schema: si se pasa, devuelve un dict validado por structured outputs.
    """
    kwargs: dict[str, Any] = {}
    output_config: dict[str, Any] = {"effort": config.WORKER_EFFORT}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    if usar_web:
        kwargs["tools"] = _web_tools(dominios if dominios is not None else config.DOMINIOS_OFICIALES)

    contenido = f"{contexto}\n\n<tarea>\n{tarea}\n</tarea>" if contexto else f"<tarea>\n{tarea}\n</tarea>"
    messages: list[dict[str, Any]] = [{"role": "user", "content": contenido}]

    resp = None
    for _ in range(6):  # pause_turn: la búsqueda web puede pausar el turno
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
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break

    if resp.stop_reason == "refusal":
        raise RechazoModelo(f"Analista rechazó la tarea: {getattr(resp, 'stop_details', None)}")
    salida = texto(resp)
    if schema:
        return json.loads(salida)
    return salida
