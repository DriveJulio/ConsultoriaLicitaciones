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
    monkeypatch.setattr(web, "PAUSAS", config.DATA_DIR / "dominios_pausados.json")
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
    monkeypatch.setattr(web, "descargar", lambda url, **k: next(paginas))
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

    def falla(url, **k):
        raise ConnectionError("caído")

    monkeypatch.setattr(web, "descargar", falla)
    for _ in range(3):
        expedientes.ejecutar()
    assert "No se puede leer el proceso e1" in (config.OUT_DIR / "alertas.md").read_text(encoding="utf-8")


def test_boletin_sin_novedades(monkeypatch):
    (config.CONFIG_DIR / "normativa.yaml").write_text("palabras_clave_boletin: [contrataciones]\n", encoding="utf-8")
    html = open("tests/fixtures/bo_primera.html", encoding="utf-8").read()
    monkeypatch.setattr(web, "descargar", lambda url, **k: html)
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


# --- Lector (Haiku) ---------------------------------------------------------------
class _Stream:
    def __init__(self, resp):
        self.resp = resp

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.resp


def _resp(texto="", stop="end_turn", content=None, model="m"):
    return SimpleNamespace(stop_reason=stop, model=model, usage=None,
                           content=content or [SimpleNamespace(type="text", text=texto)])


def test_lector_no_resume_material_corto(monkeypatch):
    from licitaciones_ai import llm

    monkeypatch.setattr(llm, "client", lambda: (_ for _ in ()).throw(AssertionError("no debe llamar")))
    assert llm.lector("texto corto") == "texto corto"


def test_lector_parte_en_bloques_y_usa_haiku(monkeypatch):
    from licitaciones_ai import llm

    monkeypatch.setattr(config, "LECTOR_UMBRAL_CHARS", 10)
    monkeypatch.setattr(config, "LECTOR_CHARS_POR_BLOQUE", 100)
    modelos = []

    def stream(**kw):
        modelos.append(kw["model"])
        return _Stream(_resp("extracto"))

    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(messages=SimpleNamespace(stream=stream)))
    out = llm.lector("línea de material\n" * 30, "plazos")
    assert len(modelos) > 1 and set(modelos) == {config.LECTOR_MODEL}
    assert out.count("extracto") == len(modelos)


def test_analista_lee_urls_via_lector(monkeypatch):
    from licitaciones_ai import llm

    respuestas = iter([
        _resp(stop="tool_use", content=[SimpleNamespace(type="tool_use", id="u1", name="leer_url",
                                                        input={"url": "https://x.gob.ar/a", "foco": "plazos"})]),
        _resp("conclusión"),
    ])
    enviados = []

    def stream(**kw):
        enviados.append(kw)
        return _Stream(next(respuestas))

    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=stream))))
    monkeypatch.setattr(llm, "leer_url", lambda url, foco: f"<extracto url=\"{url}\">ok</extracto>")
    assert llm.analista("tarea", usar_web=True) == "conclusión"
    assert enviados[0]["model"] == config.WORKER_MODEL
    assert [t.get("name") for t in enviados[0]["tools"]] == ["web_search", "leer_url", "preguntar_al_lector", "ver_fragmento"]
    assert enviados[1]["messages"][-1]["content"][0]["tool_use_id"] == "u1"


def test_preguntar_al_lector_y_ver_fragmento(monkeypatch):
    from licitaciones_ai import llm

    monkeypatch.setattr(config, "LECTOR_UMBRAL_CHARS", 10)
    monkeypatch.setattr(config, "LECTOR_CHARS_POR_BLOQUE", 200)
    material = "\n".join(f"renglón {i}" for i in range(1, 61)) + "\nPlazo de impugnación: tres días"
    vistos = []

    def stream(**kw):
        cont = kw["messages"][0]["content"]
        vistos.append(cont)
        if "<pregunta>" in cont:
            return _Stream(_resp('"Plazo de impugnación: tres días" [L61]' if "L61|" in cont else "NO FIGURA"))
        return _Stream(_resp("extracto"))

    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(messages=SimpleNamespace(stream=stream)))
    ext = llm.lector(material)
    fid = ext.split()[1]
    assert fid in llm.FUENTES and "L1| renglón 1" in vistos[0]
    resp = llm.preguntar_al_lector(fid, "¿plazo de impugnación?")
    assert resp == '"Plazo de impugnación: tres días" [L61]'
    assert llm.ver_fragmento(fid, 60, 61) == "L60| renglón 60\nL61| Plazo de impugnación: tres días"
    assert llm.preguntar_al_lector("f_nada", "x").startswith("ERROR")


def test_descargar_respeta_robots_y_deja_bitacora(monkeypatch):
    monkeypatch.setattr(web, "_permitido", lambda url: False)
    with pytest.raises(web.BloqueadoPorRobots):
        web.descargar("https://ejemplo.gob.ar/privado", motivo="test")
    reg = state.leer_jsonl(config.DATA_DIR / "accesos.jsonl")
    assert reg[0]["resultado"] == "no leído: robots.txt" and reg[0]["motivo"] == "test"


def test_user_agent_identificado():
    assert config.USER_AGENT.startswith("LicitacionesAI/") and "contacto" in config.USER_AGENT


def test_freno_429_pausa_el_dominio(monkeypatch):
    monkeypatch.setattr(web, "_permitido", lambda url: True)
    monkeypatch.setattr(web, "_esperar_turno", lambda d: None)

    class C:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            return SimpleNamespace(status_code=429)

    monkeypatch.setattr(web, "_cliente", lambda t: C())
    with pytest.raises(web.DominioPausado):
        web.descargar("https://portal.gob.ar/x")
    monkeypatch.setattr(web, "_cliente", lambda t: (_ for _ in ()).throw(AssertionError("no debe pedir")))
    with pytest.raises(web.DominioPausado):
        web.descargar("https://portal.gob.ar/y")
    assert "frenó el acceso" in (config.OUT_DIR / "alertas.md").read_text(encoding="utf-8")


def test_robots_inaccesible_no_se_lee(monkeypatch):
    monkeypatch.setattr(web, "_esperar_turno", lambda d: None)
    monkeypatch.setattr(web, "_robots", {})

    class C:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            assert url.endswith("/robots.txt"), "no debe pedir la página"
            return SimpleNamespace(status_code=503, text="")

    monkeypatch.setattr(web, "_cliente", lambda t: C())
    with pytest.raises(web.RobotsNoDisponible):
        web.descargar("https://caido.gob.ar/x")
    assert web._robots == {}  # no se cachea: se reintenta el próximo ciclo
