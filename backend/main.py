"""
API del Copiloto de Operaciones Cloud.

Ejecutar desde la raíz del repositorio:
    uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
Interfaz: http://127.0.0.1:8000    Documentación: http://127.0.0.1:8000/docs
"""

import json
import logging
import subprocess
import sys
import time
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import seguridad
from .config import CONFIG, RAIZ
from .orquestador import Orquestador
from .proveedores import ErrorProveedor, crear_proveedor

# Logging estructurado SIN contenido de la pregunta ni de la respuesta (OWASP LLM02)
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("copiloto")


def _asegurar_datos():
    if not CONFIG.db_path.exists():
        log.info(json.dumps({"evento": "generando_dataset", "destino": str(CONFIG.db_path.parent)}))
        subprocess.run([sys.executable, str(RAIZ / "data_gen" / "generar_dataset_sintetico.py"),
                        "--out", str(CONFIG.db_path.parent)], check=True, capture_output=True)


_asegurar_datos()
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Copiloto de Operaciones Cloud", version="1.0",
              description="Asistente con grounding por tool calling y verificador de procedencia (Opción 02).")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
_orquestadores: dict[str, Orquestador] = {}


def orquestador(nombre: str) -> Orquestador:
    if nombre not in _orquestadores:
        _orquestadores[nombre] = Orquestador(crear_proveedor(nombre))
    return _orquestadores[nombre]


class Solicitud(BaseModel):
    pregunta: str = Field(..., min_length=3, max_length=CONFIG.max_largo_pregunta)
    grounding: bool = True
    proveedor: Literal["ollama", "gemini", "openai", "simulado"] = "ollama"


@app.post("/api/preguntar")
@limiter.limit(f"{CONFIG.rate_limit_por_minuto}/minute")
def preguntar(request: Request, s: Solicitud):
    t0 = time.time()
    try:
        r = orquestador(s.proveedor).responder(s.pregunta, s.grounding)
    except ErrorProveedor as e:
        log.info(json.dumps({"evento": "error_proveedor", "proveedor": s.proveedor}))
        return JSONResponse(status_code=503, content={"error": str(e)})
    log.info(json.dumps({"evento": "pregunta", "huella": seguridad.huella(s.pregunta), "largo": len(s.pregunta),
                         "proveedor": r.proveedor, "modelo": r.modelo, "grounding": s.grounding, "tipo": r.tipo,
                         "veredicto": r.verificacion["veredicto"], "tools": len(r.pasos),
                         "tokens": r.tokens_entrada + r.tokens_salida, "latencia_s": round(time.time() - t0, 3)}))
    return r.a_dict()


@app.get("/api/salud")
def salud():
    o = orquestador("simulado")
    return {"estado": "ok", "periodo_datos": o.periodo, "modo_simulado_global": CONFIG.modo_simulado,
            "proveedores": {"ollama": CONFIG.ollama_model, "gemini": CONFIG.gemini_model if CONFIG.gemini_api_key else "simulado (sin key)",
                            "openai": CONFIG.openai_model if CONFIG.openai_api_key else "simulado (sin key)", "simulado": "reglas"},
            "limites": {"max_tokens": CONFIG.max_tokens, "temperature": CONFIG.temperature,
                        "max_iteraciones": CONFIG.max_iteraciones, "rate_limit_por_minuto": CONFIG.rate_limit_por_minuto}}


@app.get("/api/ejemplos")
def ejemplos():
    ruta = CONFIG.db_path.parent / "eval" / "golden_set.json"
    if not ruta.exists():
        return []
    return [{"id": p["id"], "categoria": p["categoria"], "pregunta": p["pregunta"]}
            for p in json.loads(ruta.read_text(encoding="utf-8"))["preguntas"]]


@app.get("/")
def interfaz():
    return FileResponse(RAIZ / "frontend" / "index.html")


@app.exception_handler(Exception)
def error_generico(request: Request, exc: Exception):
    """Degradación controlada: nunca se exponen trazas internas al cliente."""
    log.info(json.dumps({"evento": "error_interno", "tipo": type(exc).__name__}))
    return JSONResponse(status_code=500, content={"error": "Error interno. Revise los logs del servidor."})
