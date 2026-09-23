"""Configuración leída de variables de entorno (.env). Ningún secreto se escribe en el código."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def _bool(nombre: str, defecto: bool = False) -> bool:
    return os.getenv(nombre, str(defecto)).strip().lower() in ("1", "true", "sí", "si", "yes")


@dataclass(frozen=True)
class Config:
    # Datos
    db_path: Path = field(default_factory=lambda: RAIZ / os.getenv("DB_PATH", "data/ade_ops.sqlite"))
    # Límites de generación (rúbrica 02: "límites de longitud de respuesta configurados")
    max_tokens: int = int(os.getenv("RESPUESTA_MAX_TOKENS", "600"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.1"))
    max_iteraciones: int = int(os.getenv("MAX_ITERACIONES", "5"))
    max_reintentos_tool: int = int(os.getenv("MAX_REINTENTOS_TOOL", "2"))
    max_filas_tool: int = int(os.getenv("MAX_FILAS_TOOL", "25"))
    max_largo_pregunta: int = int(os.getenv("MAX_LARGO_PREGUNTA", "500"))
    timeout_s: float = float(os.getenv("TIMEOUT_PROVEEDOR_S", "120"))
    # Proveedores
    modo_simulado: bool = _bool("MODO_SIMULADO", False)
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "16384"))
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")  # mantiene el modelo cargado entre consultas
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    gemini_base_url: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    # Seguridad
    rate_limit_por_minuto: int = int(os.getenv("RATE_LIMIT_POR_MINUTO", "20"))
    canario: str = os.getenv("TOKEN_CANARIO", "CANARIO-7F3A")


CONFIG = Config()
