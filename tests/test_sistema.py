import json
from types import SimpleNamespace

import pytest

from licitaciones_ai import config, state
from licitaciones_ai.monitors import boletin, expedientes, web


@pytest.fixture(autouse=True)
def raiz_temporal(tmp_path, monkeypatch):
    for d in ("CONFIG_DIR", "DATA_DIR", "REPORTS_DIR", "KNOWLEDGE_DIR", "OUT_DIR"):
        monkeypatch.setattr(config, d, tmp_path / d.lower())
        (tmp_path / d.lower()).mkdir()
    monkeypatch.setattr(state, "REGISTRO", config.DATA_DIR / "registro.jsonl")
    monkeypatch.setattr(expedientes, "DIR_ESTADO", config.DATA_DIR / "expedientes")
    monkeypatch.setattr(boletin, "ESTADO", config.DATA_DIR / "boletin_estado.json")
    monkeypatch.setattr(boletin, "NOVEDADES", config.KNOWLEDGE_DIR / "nov.md")
    return tmp_path


def test_extraer_y_filtrar_avisos_bo():
    html = open("tests/fixtures/bo_primera.html", encoding="utf-8").read()
    avisos = boletin.extraer_avisos(html)
    assert len(avisos) == 2
    rel = boletin.filtrar(avisos, ["contrataciones"])
    assert [a["url"] for a in rel] == ["https://www.boletinoficial.gob.ar/detalleAviso/primera/330001/20261102"]


def test_normalizar_ignora_ruido():
    a = expedientes.normalizar("Acta de apertura\nActualizado 10:31:02\n")
    b = expedientes.normalizar("Acta de apertura\nActualizado 18:02:55\n")
    assert a == b


def test_registrar_alerta_genera_notificacion():
    state.registrar("alerta", "Plazo de impugnación", "Vence el viernes", "alta", "test")
    assert "Plazo de impugnación" in (config.OUT_DIR / "alertas.md").read_text(encoding="utf-8")
    assert state.leer_jsonl(state.REGISTRO)[0]["tipo"] == "alerta"


def _yaml_expediente(url="https://ejemplo.gob.ar/p"):
    (config.CONFIG_DIR / "expedientes.yaml").write_text(
        f"expedientes:\n  - id: e1\n    nombre: LP 1/2026\n    url: {url}\n    activo: true\n", encoding="utf-8")


def test_expedientes_linea_base_y_novedad(monkeypatch):
    _yaml_expediente()
    paginas = iter([
        "<html><body><p>Convocatoria</p></body></html>",
        "<html><body><p>Convocatoria</p><a href='/acta.pdf'>Acta de apertura</a></body></html>",
    ])
    monkeypatch.setattr(web, "descargar", lambda url, timeout=45.0: next(paginas))
    llamados = []

    def analista_falso(tarea, contexto="", usar_web=False, dominios=None, schema=None, max_tokens=0):
        llamados.append(contexto)
        return {"hay_novedad_sustantiva": True, "etapa": "Apertura", "resumen": "Se publicó el acta",
                "documentos_nuevos": ["acta.pdf"], "plazos": [], "urgencia": "media", "acciones": []}

    monkeypatch.setattr(expedientes.llm, "analista", analista_falso)

    r1 = open(expedientes.ejecutar(), encoding="utf-8").read()
    assert "primera foto" in r1 and not llamados
    r2 = open(expedientes.ejecutar(), encoding="utf-8").read()
    assert "Se publicó el acta" in r2
    assert "acta.pdf" in llamados[0]
    assert "Novedad en LP 1/2026" in (config.OUT_DIR / "alertas.md").read_text(encoding="utf-8")


def test_expediente_con_fallas_alerta_a_la_tercera(monkeypatch):
    _yaml_expediente()

    def falla(url, timeout=45.0):
        raise ConnectionError("caído")

    monkeypatch.setattr(web, "descargar", falla)
    for _ in range(3):
        expedientes.ejecutar()
    assert "No se puede leer el proceso e1" in (config.OUT_DIR / "alertas.md").read_text(encoding="utf-8")


def test_boletin_sin_novedades(monkeypatch):
    (config.CONFIG_DIR / "normativa.yaml").write_text("palabras_clave_boletin: [contrataciones]\n", encoding="utf-8")
    html = open("tests/fixtures/bo_primera.html", encoding="utf-8").read()
    monkeypatch.setattr(web, "descargar", lambda url, timeout=45.0: html)
    monkeypatch.setattr(boletin.llm, "analista", lambda *a, **k: {
        "relevante": False, "tipo_cambio": "ninguno", "norma": "", "normas_afectadas": [],
        "resumen": "", "vigencia": "", "impacto": "nulo", "acciones": []})
    rep = open(boletin.ejecutar(), encoding="utf-8").read()
    assert "Sin novedades" in rep
    assert json.loads((config.DATA_DIR / "boletin_estado.json").read_text())["procesados"]


def test_orquestador_loop_herramientas(monkeypatch):
    from licitaciones_ai.agents import orquestador as orq

    respuestas = iter([
        SimpleNamespace(stop_reason="tool_use", content=[
            SimpleNamespace(type="tool_use", id="t1", name="registrar",
                            input={"tipo": "decision", "titulo": "X", "detalle": "Y", "prioridad": "baja"})]),
        SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="listo")]),
    ])
    o = orq.Orquestador("especialista", "sys")
    monkeypatch.setattr(o, "_llamar", lambda: next(respuestas))
    assert o.enviar("hola") == "listo"
    assert o.messages[2]["content"][0]["tool_use_id"] == "t1"
    assert o.registros[0]["titulo"] == "X"


def test_leer_archivo_bloquea_rutas_fuera():
    from licitaciones_ai.agents.orquestador import _leer_archivo

    assert _leer_archivo("../../etc/passwd").startswith("ERROR")
