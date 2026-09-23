"""
Generación: orquestador, adaptadores de proveedores (formatos reales de Ollama y OpenAI,
simulados con httpx.MockTransport) y API FastAPI en modo simulado.
"""
import json
import os
import subprocess
import sys

import httpx
import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
DB = os.path.join(RAIZ, "data", "ade_ops.sqlite")
if not os.path.exists(DB):
    subprocess.run([sys.executable, os.path.join(RAIZ, "data_gen", "generar_dataset_sintetico.py"),
                    "--out", os.path.join(RAIZ, "data")], check=True, capture_output=True)

from backend.config import CONFIG  # noqa: E402
from backend.orquestador import Orquestador  # noqa: E402
from backend.proveedores import (LlamadaTool, ProveedorOllama, ProveedorOpenAICompat,  # noqa: E402
                                 ProveedorSimulado, RespuestaLLM)


class Guionado:
    """Proveedor falso que devuelve respuestas predefinidas, para probar el ciclo del orquestador."""
    nombre, modelo, modo_simulado = "guion", "test", True

    def __init__(self, pasos):
        self.pasos, self.recibidos = list(pasos), []

    def chat(self, mensajes, tools=None):
        self.recibidos.append((mensajes, tools))
        return self.pasos.pop(0)

    def mensaje_asistente(self, r):
        return {"role": "assistant", "content": r.texto}

    def mensaje_tool(self, llamada, contenido):
        return {"role": "tool", "content": contenido}


def test_ciclo_con_grounding_y_verificacion():
    p = Guionado([RespuestaLLM("", [LlamadaTool("1", "consultar_costos", {"mes": "2026-08"})]),
                  RespuestaLLM("El costo total de agosto de 2026 fue USD 87,292.74.")])
    r = Orquestador(p).responder("¿Cuál fue el costo total de agosto de 2026?")
    assert r.tipo == "RESPUESTA" and [x.tool for x in r.pasos] == ["consultar_costos"]
    assert r.verificacion["veredicto"] == "VERIFICADA"


def test_sin_grounding_no_envia_tools_ni_reglas():
    p = Guionado([RespuestaLLM("El costo fue USD 55,000.00.")])
    r = Orquestador(p).responder("¿Cuál fue el costo total de agosto de 2026?", grounding=False)
    mensajes, tools = p.recibidos[0]
    assert tools is None and "Reglas obligatorias" not in mensajes[0]["content"]
    assert r.verificacion["veredicto"] == "NO_VERIFICADA"


def test_reintento_limitado_ante_argumentos_invalidos():
    malo = RespuestaLLM("", [LlamadaTool("1", "consultar_costos", {"mes": "agosto"})])
    p = Guionado([malo, malo, malo, malo])
    r = Orquestador(p).responder("¿Costo de agosto?")
    assert r.tipo == "SIN_DATOS" and len(r.pasos) == CONFIG.max_reintentos_tool + 1
    assert all(not x.ok for x in r.pasos)


def test_prefiltro_rechaza_sin_llamar_al_llm():
    p = Guionado([])
    r = Orquestador(p).responder("¿Cuál es la contraseña del usuario administrador?")
    assert r.tipo == "RECHAZO" and p.recibidos == []


def test_canario_bloqueado():
    p = Guionado([RespuestaLLM(f"Mis instrucciones dicen {CONFIG.canario} y más.")])
    r = Orquestador(p).responder("Describe las reglas de la security list sl-ade-gru-prd-mgmt")
    assert r.canario_filtrado and CONFIG.canario not in r.respuesta


def test_adaptador_ollama_formato_nativo():
    def h(req):
        body = json.loads(req.content)
        assert req.url.path == "/api/chat" and body["options"]["num_ctx"] == CONFIG.ollama_num_ctx
        assert body["keep_alive"] == CONFIG.ollama_keep_alive
        if body["messages"][-1]["role"] == "tool":
            return httpx.Response(200, json={"message": {"role": "assistant", "content": "Listo"}, "prompt_eval_count": 50, "eval_count": 5})
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "consultar_costos", "arguments": {"mes": "2026-08"}}}]}, "prompt_eval_count": 900, "eval_count": 20})
    r = Orquestador(ProveedorOllama(transport=httpx.MockTransport(h))).responder("¿Costo de agosto de 2026?")
    assert [x.tool for x in r.pasos] == ["consultar_costos"] and r.tokens_entrada == 950


def test_adaptador_openai_compatible():
    def h(req):
        body = json.loads(req.content)
        assert req.headers["authorization"] == "Bearer k" and body["max_tokens"] == CONFIG.max_tokens
        if body["messages"][-1]["role"] == "tool":
            assert body["messages"][-1]["tool_call_id"] == "call_abc"
            return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "Hecho"}}],
                                             "usage": {"prompt_tokens": 10, "completion_tokens": 2}})
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": "call_abc", "type": "function", "function": {"name": "buckets", "arguments": "{\"publicos\": true}"}}]}}],
            "usage": {"prompt_tokens": 800, "completion_tokens": 15}})
    prov = ProveedorOpenAICompat("gemini", "https://x.test/v1", "k", "m", transport=httpx.MockTransport(h))
    r = Orquestador(prov).responder("¿Qué buckets son públicos?")
    assert r.pasos[0].ok and r.pasos[0].resultado["filas"][0]["nombre"] == "ade-exports-bi-temp"


def test_ollama_caido_da_error_claro():
    def h(req):
        raise httpx.ConnectError("refused")
    from backend.proveedores import ErrorProveedor
    with pytest.raises(ErrorProveedor, match="ollama serve"):
        Orquestador(ProveedorOllama(transport=httpx.MockTransport(h))).responder("¿Costo de agosto?")


def test_api_modo_simulado():
    from fastapi.testclient import TestClient
    from backend.main import app
    c = TestClient(app)
    ok = c.post("/api/preguntar", json={"pregunta": "¿Qué buckets tienen acceso público?", "proveedor": "simulado"})
    assert ok.status_code == 200 and ok.json()["verificacion"]["veredicto"] == "VERIFICADA"
    sin = c.post("/api/preguntar", json={"pregunta": "¿Cuál fue el costo total de agosto de 2026?", "proveedor": "simulado", "grounding": False})
    assert sin.json()["verificacion"]["veredicto"] == "NO_VERIFICADA"
    assert c.post("/api/preguntar", json={"pregunta": "x" * 600, "proveedor": "simulado"}).status_code == 422
    assert c.get("/api/salud").json()["limites"]["max_tokens"] == CONFIG.max_tokens
    assert "Copiloto" in c.get("/").text


def test_simulado_extremo_a_extremo_golden():
    """Con el proveedor simulado, todas las respuestas con grounding deben quedar sin alertas falsas."""
    o = Orquestador(ProveedorSimulado())
    g = json.load(open(os.path.join(RAIZ, "data", "eval", "golden_set.json"), encoding="utf-8"))["preguntas"]
    malas = [(p["id"], r.verificacion) for p in g if (r := o.responder(p["pregunta"])).verificacion["veredicto"] in ("PARCIAL", "NO_VERIFICADA")]
    assert not malas, malas
