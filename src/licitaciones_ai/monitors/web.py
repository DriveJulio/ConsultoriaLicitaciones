"""Descarga y normalización de páginas públicas."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import config


def descargar(url: str, timeout: float = 45.0) -> str:
    import httpx

    with httpx.Client(
        headers={"User-Agent": config.USER_AGENT, "Accept-Language": "es-AR,es;q=0.9"},
        follow_redirects=True,
        timeout=timeout,
    ) as c:
        r = c.get(url)
        r.raise_for_status()
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
