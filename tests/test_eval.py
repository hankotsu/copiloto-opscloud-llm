"""
Instrumento de medición: los errores del proveedor (429, 503, sin conexión) no deben
contaminar las métricas. Hallazgo del 23/09: con la cuota de Gemini agotada, run_eval
registraba cada 429 como una negativa (SIN_CIFRAS), lo que inflaba la tasa de "no inventó".
"""
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import httpx
import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "eval"))
DB = os.path.join(RAIZ, "data", "ade_ops.sqlite")
if not os.path.exists(DB):
    subprocess.run([sys.executable, os.path.join(RAIZ, "data_gen", "generar_dataset_sintetico.py"),
                    "--out", os.path.join(RAIZ, "data")], check=True, capture_output=True)

import run_eval  # noqa: E402
from backend import proveedores  # noqa: E402
from backend.proveedores import ErrorProveedor, ProveedorOpenAICompat  # noqa: E402

PROV = SimpleNamespace(nombre="prueba", modelo="m", modo_simulado=False)


def _fila(id_, grounding, correcta, veredicto, tipo="RESPUESTA", tokens=100):
    return {"corrida": 1, "id": id_, "categoria": "finops", "tipo_esperado": "decimal", "grounding": grounding,
            "correcta": correcta, "motivo": "", "tipo": tipo, "veredicto": veredicto, "respuesta": "x",
            "herramientas": [], "tokens": tokens, "latencia_s": 1.0, "verificacion": {"veredicto": veredicto}}


def test_resumir_excluye_errores_del_proveedor():
    filas = [
        _fila("G13", False, False, "NO_VERIFICADA"),                       # inventó y fue alertada
        _fila("G17", False, False, "SIN_CIFRAS"),                          # se negó de verdad
        run_eval.fila_error(1, "G18", "finops", "decimal", False, "gemini respondió 429"),
        _fila("G13", True, True, "VERIFICADA"),
        run_eval.fila_error(1, "G17", "finops", "decimal", True, "gemini respondió 503"),
    ]
    args = SimpleNamespace(corridas=1)
    r = run_eval.resumir(filas, [], PROV, args)
    sin, con = r["por_modo"]["sin"], r["por_modo"]["con"]
    assert r["errores_proveedor"] == {"total": 2, "sin": 1, "con": 1, "inyeccion": 0}
    # El 429 NO se cuenta como negativa: solo hay 1 SIN_CIFRAS real.
    assert sin["veredictos"]["SIN_CIFRAS"] == 1 and sin["consultas_validas"] == 2
    # El 503 NO se cuenta como respuesta incorrecta: con grounding queda 1 de 1.
    assert con["exactitud_pct_media"] == 100.0 and con["consultas_validas"] == 1
    # Tokens y latencia promedian solo respuestas reales (los errores valen 0).
    assert sin["tokens_promedio"] == 100


def test_modo_solo_con_errores_no_rompe_el_resumen():
    filas = [run_eval.fila_error(1, "G13", "finops", "decimal", False, "gemini respondió 429")]
    r = run_eval.resumir(filas, [], PROV, SimpleNamespace(corridas=1), abortada="detenida")
    assert r["por_modo"]["sin"] == {"consultas_validas": 0, "errores_proveedor": 1}
    assert r["abortada"] == "detenida"


class _Caido:
    nombre, modelo, modo_simulado = "caido", "m", False

    def __init__(self):
        self.llamadas = 0

    def chat(self, mensajes, tools=None):
        self.llamadas += 1
        raise ErrorProveedor("caido respondió 429")


def test_corrida_se_detiene_tras_errores_seguidos(tmp_path, monkeypatch):
    caido = _Caido()
    monkeypatch.setattr(run_eval, "RAIZ", str(tmp_path))
    monkeypatch.setattr(run_eval, "crear_proveedor", lambda nombre: caido)
    args = SimpleNamespace(proveedor="caido", corridas=1, modos="sin,con", ids="G13,G17", limite=0, pausa=0,
                           max_errores_seguidos=3)
    run_eval.correr(args)
    assert caido.llamadas == 3                       # la 4.ª consulta ya no se envía
    [salida] = list((tmp_path / "eval" / "resultados").iterdir())
    filas = [json.loads(x) for x in (salida / "respuestas.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(filas) == 3 and all(f["tipo"] == "ERROR" and f["veredicto"] == "ERROR" for f in filas)
    resumen = json.loads((salida / "resumen.json").read_text(encoding="utf-8"))
    assert resumen["errores_proveedor"]["total"] == 3 and resumen["abortada"]
    md = (salida / "RESUMEN.md").read_text(encoding="utf-8")
    assert "excluidas por error del proveedor" in md and "⛔" in md
    assert "None" not in md                          # sin datos se muestra como "—"
    assert "ERROR" in (salida / "PARES.md").read_text(encoding="utf-8")


def test_429_por_cuota_diaria_no_reintenta():
    llamadas = []

    def h(req):
        llamadas.append(req)
        return httpx.Response(429, json={"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "details": [
            {"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}})
    prov = ProveedorOpenAICompat("gemini", "https://x.test/v1", "k", "m", transport=httpx.MockTransport(h))
    with pytest.raises(ErrorProveedor, match="cuota diaria"):
        prov.chat([{"role": "user", "content": "hola"}])
    assert len(llamadas) == 1


def test_429_por_minuto_si_reintenta(monkeypatch):
    monkeypatch.setattr(proveedores.time, "sleep", lambda s: None)
    respuestas = [httpx.Response(429, json={"error": {"code": 429, "details": [
                      {"violations": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]}]}}),
                  httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "OK"}}], "usage": {}})]
    prov = ProveedorOpenAICompat("gemini", "https://x.test/v1", "k", "m",
                                 transport=httpx.MockTransport(lambda req: respuestas.pop(0)))
    assert prov.chat([{"role": "user", "content": "hola"}]).texto == "OK"
