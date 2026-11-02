"""Persistencia simple en archivos (JSON/JSONL/Markdown) versionados en el repo."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config


def leer_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def escribir_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def agregar_jsonl(path: Path, registro: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def leer_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


REGISTRO = config.DATA_DIR / "registro.jsonl"


def registrar(tipo: str, titulo: str, detalle: str, prioridad: str = "media", origen: str = "") -> dict:
    """Registra una decisión, alerta o propuesta. Las alertas también van a out/alertas.md."""
    reg = {
        "fecha": config.ahora().isoformat(timespec="minutes"),
        "tipo": tipo,
        "titulo": titulo,
        "detalle": detalle,
        "prioridad": prioridad,
        "origen": origen,
    }
    agregar_jsonl(REGISTRO, reg)
    if tipo == "alerta":
        agregar_alerta(f"[{prioridad.upper()}] {titulo}", detalle)
    return reg


def agregar_alerta(titulo: str, cuerpo: str) -> None:
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (config.OUT_DIR / "alertas.md").open("a", encoding="utf-8") as f:
        f.write(f"## {titulo}\n\n{cuerpo.strip()}\n\n---\n\n")


def guardar_reporte(nombre: str, contenido: str) -> Path:
    fecha = config.ahora()
    path = config.REPORTS_DIR / fecha.strftime("%Y-%m-%d") / f"{fecha:%H%M}-{nombre}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    from . import llm

    path.write_text(contenido.strip() + llm.resumen_uso() + "\n", encoding="utf-8")
    if llm.USO:
        agregar_jsonl(config.DATA_DIR / "uso_tokens.jsonl",
                      {"fecha": fecha.isoformat(timespec="minutes"), "tarea": nombre, "uso": llm.USO})
    return path
