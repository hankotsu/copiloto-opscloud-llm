"""Controles deterministas previos y posteriores al LLM (no dependen de que el modelo obedezca)."""
from __future__ import annotations

import hashlib
import re
import unicodedata

PATRON_SENSIBLE = re.compile(
    r"contrase(ñ|n)a|password|passwd|credencial|api[\s_-]?key|llave privada|private key|secret|token de acceso", re.I)
PATRON_INYECCION_DIRECTA = re.compile(
    r"ignora (todas )?(las|tus) instrucciones|olvida (tus|las) instrucciones|act[uú]a como|system prompt|prompt de sistema|"
    r"modo (desarrollador|diagn[oó]stico)|jailbreak", re.I)


def sanitizar(texto: str, max_largo: int) -> str:
    """Normaliza Unicode, elimina caracteres de control y recorta."""
    t = unicodedata.normalize("NFKC", texto)
    t = "".join(c for c in t if c in "\n\t" or unicodedata.category(c)[0] != "C")
    return t.strip()[:max_largo]


def prefiltro(pregunta: str) -> tuple[str, str] | None:
    """Devuelve (tipo, mensaje) si la pregunta se resuelve sin llamar al LLM."""
    if PATRON_SENSIBLE.search(pregunta):
        return "RECHAZO", "No puedo entregar credenciales, contraseñas ni otra información sensible."
    if PATRON_INYECCION_DIRECTA.search(pregunta):
        return "RECHAZO", "La consulta intenta modificar el comportamiento del asistente; no se procesa."
    return None


def filtrar_canario(texto: str, canario: str) -> tuple[str, bool]:
    """LLM07: si el token canario aparece en la salida, el prompt de sistema se filtró."""
    if canario and canario.lower() in texto.lower():
        return "RECHAZO: la respuesta fue bloqueada porque exponía instrucciones internas.", True
    return texto, False


def huella(texto: str) -> str:
    """Hash corto para correlacionar logs sin guardar el contenido de la pregunta (LLM02)."""
    return hashlib.sha256(texto.encode()).hexdigest()[:12]
