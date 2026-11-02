"""Orquestador sobre Claude Fable 5.1 con loop de herramientas propio.

El orquestador piensa y decide; el trabajo lo hacen analistas Opus 5.5 (esfuerzo medio)
a través de la herramienta `delegar_a_analista`. El historial es append-only (requisito
de "preserved thinking" en Fable 5.1): nunca editamos turnos anteriores.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from .. import config, llm, state

HERRAMIENTAS: list[dict[str, Any]] = [
    {
        "name": "delegar_a_analista",
        "description": (
            "Delega una tarea autocontenida a un analista (Claude Opus 5.5, esfuerzo medio) y devuelve su "
            "resultado. Usalo para leer y analizar normas, pliegos, actas, dictámenes o publicaciones, y para "
            "investigar en fuentes oficiales con usar_web=true. Podés llamar varias veces en paralelo."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "tarea": {"type": "string", "description": "Qué tiene que hacer y en qué formato responder."},
                "contexto": {"type": "string", "description": "Material que necesita (texto, extractos, URLs)."},
                "usar_web": {"type": "boolean", "description": "Habilita búsqueda/lectura web en dominios oficiales."},
            },
            "required": ["tarea", "contexto", "usar_web"],
            "additionalProperties": False,
        },
    },
    {
        "name": "leer_archivo",
        "description": (
            "Lee un archivo de la base de conocimiento o del estado del sistema. Rutas relativas permitidas: "
            "knowledge/*, config/*, data/*, reports/*. Ej: knowledge/marco_normativo.md, config/expedientes.yaml. "
            "Si el archivo es largo, un lector devuelve un extracto según 'foco' (qué necesitás de él)."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"ruta": {"type": "string"}, "foco": {"type": "string"}},
            "required": ["ruta", "foco"],
            "additionalProperties": False,
        },
    },
    {
        "name": "registrar",
        "description": (
            "Registra una decisión, alerta o propuesta. 'alerta' = algo que el equipo humano tiene que ver hoy "
            "(se notifica). 'propuesta' = mejora para aprobación humana. 'decision' = criterio adoptado."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": ["decision", "alerta", "propuesta"]},
                "titulo": {"type": "string"},
                "detalle": {"type": "string"},
                "prioridad": {"type": "string", "enum": ["alta", "media", "baja"]},
            },
            "required": ["tipo", "titulo", "detalle", "prioridad"],
            "additionalProperties": False,
        },
    },
]

_PERMITIDOS = ("knowledge", "config", "data", "reports")


def _leer_archivo(ruta: str, foco: str = "") -> str:
    p = (config.ROOT / ruta).resolve()
    root = config.ROOT.resolve()
    if not any(p.is_relative_to(root / d) for d in _PERMITIDOS):
        return f"ERROR: ruta no permitida ({ruta}). Solo {', '.join(_PERMITIDOS)}."
    if p.is_dir():
        return "\n".join(sorted(str(x.relative_to(root)) for x in p.rglob("*") if x.is_file()))[:20000]
    if not p.exists():
        return f"ERROR: no existe {ruta}"
    contenido = p.read_text(encoding="utf-8")
    # Archivos largos los lee Haiku: el orquestador (Fable) recibe solo el extracto.
    return llm.lector(contenido, foco or "todo lo relevante para la tarea")


class Orquestador:
    def __init__(self, nombre: str, system: str, max_iteraciones: int = 25):
        self.nombre = nombre
        self.system = system
        self.max_iteraciones = max_iteraciones
        self.messages: list[dict[str, Any]] = []
        self.registros: list[dict] = []
        self._handlers: dict[str, Callable[[dict], str]] = {
            "delegar_a_analista": self._delegar,
            "leer_archivo": lambda i: _leer_archivo(i["ruta"], i.get("foco", "")),
            "registrar": self._registrar,
        }

    # --- herramientas ---------------------------------------------------------
    def _delegar(self, inp: dict) -> str:
        return str(llm.analista(inp["tarea"], inp.get("contexto", ""), usar_web=inp.get("usar_web", False)))

    def _registrar(self, inp: dict) -> str:
        reg = state.registrar(inp["tipo"], inp["titulo"], inp["detalle"], inp["prioridad"], origen=self.nombre)
        self.registros.append(reg)
        return "registrado"

    def _ejecutar(self, bloque) -> dict:
        try:
            salida = self._handlers[bloque.name](dict(bloque.input))
            return {"type": "tool_result", "tool_use_id": bloque.id, "content": salida}
        except Exception as e:  # el error vuelve al modelo, no se pierde
            return {"type": "tool_result", "tool_use_id": bloque.id, "content": f"ERROR: {e}", "is_error": True}

    # --- loop -----------------------------------------------------------------
    def _llamar(self):
        with llm.client().beta.messages.stream(
            model=config.ORQUESTADOR_MODEL,
            max_tokens=64000,
            system=[{"type": "text", "text": self.system, "cache_control": {"type": "ephemeral"}}],
            tools=HERRAMIENTAS,
            messages=self.messages,
            output_config={"effort": config.ORQUESTADOR_EFFORT},
            betas=[config.FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            resp = stream.get_final_message()
        llm._contar(resp)
        return resp

    def enviar(self, mensaje: str) -> str:
        """Envía un mensaje y corre el loop de herramientas hasta la respuesta final."""
        self.messages.append({"role": "user", "content": mensaje})
        for _ in range(self.max_iteraciones):
            resp = self._llamar()
            self.messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason == "refusal":
                raise llm.RechazoModelo(f"{self.nombre}: {getattr(resp, 'stop_details', None)}")
            if resp.stop_reason == "pause_turn":
                continue
            usos = [b for b in resp.content if b.type == "tool_use"]
            if resp.stop_reason != "tool_use" or not usos:
                return llm.texto(resp)
            with ThreadPoolExecutor(max_workers=4) as pool:
                resultados = list(pool.map(self._ejecutar, usos))
            # Todos los tool_result en un único mensaje de usuario.
            self.messages.append({"role": "user", "content": resultados})
        return f"[{self.nombre}] Se alcanzó el máximo de iteraciones sin respuesta final."


def especialista() -> Orquestador:
    from .prompts import SYSTEM_ESPECIALISTA

    return Orquestador("especialista", SYSTEM_ESPECIALISTA)


def asesor() -> Orquestador:
    from .prompts import SYSTEM_ASESOR

    return Orquestador("asesor", SYSTEM_ASESOR)


def resumen_registros(regs: list[dict]) -> str:
    if not regs:
        return "_Sin registros._"
    return "\n".join(f"- **{r['tipo']}** [{r['prioridad']}] {r['titulo']}" for r in regs)


def dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


__all__ = ["Orquestador", "especialista", "asesor", "resumen_registros", "dump", "Path"]
