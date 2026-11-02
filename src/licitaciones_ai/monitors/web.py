"""Descarga y normalización de páginas públicas."""
from __future__ import annotations

import hashlib
import re
import threading
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from .. import config


class BloqueadoPorRobots(PermissionError):
    """El robots.txt del sitio no permite leer esa URL: no se lee."""


class DominioPausado(PermissionError):
    """El portal nos frenó (403/429/503): se pausa 24 h y se pasa a revisión manual."""


HORAS_PAUSA = 24
CODIGOS_FRENO = {403, 429, 503}
PAUSAS = config.DATA_DIR / "dominios_pausados.json"


_lock = threading.Lock()
_ultimo_pedido: dict[str, float] = {}
_robots: dict[str, RobotFileParser | None] = {}


def _cliente(timeout: float):
    import httpx

    return httpx.Client(
        headers={"User-Agent": config.USER_AGENT, "Accept-Language": "es-AR,es;q=0.9"},
        follow_redirects=True,
        timeout=timeout,
    )


def _esperar_turno(dominio: str) -> None:
    """Respeta un intervalo mínimo entre pedidos al mismo dominio."""
    while True:
        with _lock:
            espera = _ultimo_pedido.get(dominio, 0) + config.SEGUNDOS_ENTRE_PEDIDOS - time.monotonic()
            if espera <= 0:
                _ultimo_pedido[dominio] = time.monotonic()
                return
        time.sleep(espera)


class RobotsNoDisponible(PermissionError):
    """No se pudo leer robots.txt (sitio caído o error): no se lee hasta el próximo ciclo."""


def _permitido(url: str) -> bool:
    u = urlparse(url)
    base = f"{u.scheme}://{u.netloc}"
    if base not in _robots:
        try:
            _esperar_turno(u.netloc)
            with _cliente(20) as c:
                r = c.get(base + "/robots.txt")
        except Exception as e:
            raise RobotsNoDisponible(f"{base}: {type(e).__name__}") from e
        if r.status_code >= 500 or r.status_code in (401, 403, 429):
            raise RobotsNoDisponible(f"{base}: HTTP {r.status_code}")  # no se cachea: se reintenta el próximo ciclo
        rp: RobotFileParser | None = None  # 404 u otro 4xx: el sitio no declara restricciones
        if r.status_code < 400:
            rp = RobotFileParser()
            rp.parse(r.text.splitlines())
        _robots[base] = rp
    rp = _robots[base]
    return True if rp is None else rp.can_fetch(config.USER_AGENT, url)


def _bitacora(url: str, motivo: str, resultado: str) -> None:
    from .. import state

    state.agregar_jsonl(config.DATA_DIR / "accesos.jsonl", {
        "fecha": config.ahora().isoformat(timespec="seconds"), "url": url, "motivo": motivo, "resultado": resultado,
    })


def descargar(url: str, timeout: float = 45.0, motivo: str = "") -> str:
    """Descarga una página pública respetando robots.txt, ritmo por dominio y dejando bitácora."""
    from .. import state

    dominio = urlparse(url).netloc
    pausas = state.leer_json(PAUSAS, {})
    if dominio in pausas and pausas[dominio] > config.ahora().isoformat():
        _bitacora(url, motivo, f"no leído: dominio pausado hasta {pausas[dominio]}")
        raise DominioPausado(f"{dominio} pausado hasta {pausas[dominio]}")
    try:
        permitido = _permitido(url)
    except RobotsNoDisponible as e:
        _bitacora(url, motivo, f"no leído: robots.txt no disponible ({e})")
        raise
    if not permitido:
        _bitacora(url, motivo, "no leído: robots.txt")
        raise BloqueadoPorRobots(url)
    _esperar_turno(dominio)
    try:
        with _cliente(timeout) as c:
            r = c.get(url)
        if r.status_code in CODIGOS_FRENO:
            from datetime import timedelta

            hasta = (config.ahora() + timedelta(hours=HORAS_PAUSA)).isoformat(timespec="minutes")
            pausas[dominio] = hasta
            state.escribir_json(PAUSAS, pausas)
            state.registrar("alerta", f"Portal {dominio} frenó el acceso (HTTP {r.status_code})",
                            f"Se pausa el acceso automático hasta {hasta}. Revisar a mano: {url}", "media", "web")
            _bitacora(url, motivo, f"freno HTTP {r.status_code}: pausado hasta {hasta}")
            raise DominioPausado(f"{dominio} respondió {r.status_code}")
        r.raise_for_status()
    except DominioPausado:
        raise
    except Exception as e:
        _bitacora(url, motivo, f"error: {type(e).__name__}")
        raise
    _bitacora(url, motivo, f"ok {r.status_code}")
    return r.text


def texto_visible(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "head"]):
        tag.decompose()
    lineas = (re.sub(r"\s+", " ", l).strip() for l in soup.get_text("\n").splitlines())
    return "\n".join(l for l in lineas if l)


def enlaces(html: str, base: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    vistos, out = set(), []
    for a in soup.find_all("a", href=True):
        href = urljoin(base, a["href"])
        if href.startswith("javascript") or href in vistos:
            continue
        vistos.add(href)
        out.append({"url": href, "texto": re.sub(r"\s+", " ", a.get_text(" ")).strip()})
    return out


def huella(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()
