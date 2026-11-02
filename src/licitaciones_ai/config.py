"""Configuración central: modelos, rutas y zona horaria."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# --- Modelos -----------------------------------------------------------------
# Orquestadores (Especialista y Asesor): Claude Fable 5.1.
ORQUESTADOR_MODEL = os.getenv("LIC_ORQ_MODEL", "claude-fable-5-1")
ORQUESTADOR_EFFORT = os.getenv("LIC_ORQ_EFFORT", "high")

# Analistas que hacen el trabajo: Claude Opus 5.5 con esfuerzo medio.
WORKER_MODEL = os.getenv("LIC_WORKER_MODEL", "claude-opus-5-5")
WORKER_EFFORT = os.getenv("LIC_WORKER_EFFORT", "medium")

# Fallback del lado del servidor si un modelo rechaza la consulta.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# --- Tiempo ------------------------------------------------------------------
TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def ahora() -> datetime:
    return datetime.now(TZ)


# --- Rutas -------------------------------------------------------------------
def _raiz() -> Path:
    if os.getenv("LIC_ROOT"):
        return Path(os.environ["LIC_ROOT"])
    repo = Path(__file__).resolve().parents[2]  # instalación editable / ejecución desde src
    return repo if (repo / "config").is_dir() else Path.cwd()


ROOT = _raiz()
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
KNOWLEDGE_DIR = ROOT / "knowledge"
OUT_DIR = ROOT / "out"  # alertas efímeras que el workflow convierte en issues

# Dominios oficiales que los analistas pueden consultar por web.
DOMINIOS_OFICIALES = [
    "boletinoficial.gob.ar",
    "argentina.gob.ar",
    "infoleg.gob.ar",
    "servicios.infoleg.gob.ar",
    "comprar.gob.ar",
    "contratar.gob.ar",
    "saij.gob.ar",
    "ptn.gob.ar",
    "sigen.gob.ar",
]

USER_AGENT = "Mozilla/5.0 (compatible; LicitacionesAI/0.1; monitoreo de informacion publica)"
