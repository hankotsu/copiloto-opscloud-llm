"""
Puntaje de una respuesta en texto libre contra el golden set.

Criterio "recall": la respuesta es correcta si CONTIENE el valor esperado (con la
tolerancia declarada en el golden set). Una respuesta puede traer datos extra.
Es determinista y gratuito (mismo espíritu que el harness de la Sesión 5).
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.verificador import MESES, RE_ENTIDAD, RE_RUIDO, _fechas, extraer_numeros  # noqa: E402

RESPONDIBLES = ("entero", "decimal", "lista", "texto", "objeto")
RE_NO_HAY = re.compile(r"no (hay|tengo|dispongo de|cuento con) (datos|informaci[oó]n|registros)|fuera del periodo|sin datos", re.I)
RE_CERO = re.compile(r"\b(0|cero|ninguna?|no (hay|existen|se encontraron))\b", re.I)


def _valores(texto: str) -> list[float]:
    limpio = RE_RUIDO.sub(" ", RE_ENTIDAD.sub(" ", _fechas(texto.replace("**", ""))[1]))
    return [v for n in extraer_numeros(limpio) for v, _ in n["cands"]]


def _contiene_num(texto: str, x: float, tol_rel: float | None, entero: bool = False) -> bool:
    tol = 0.5 if entero else max(abs(x) * (tol_rel or 0.5) / 100, 0.006)
    return any(abs(v - x) <= tol for v in _valores(texto))


def _contiene_fecha(texto: str, iso: str) -> bool:
    if iso in texto:
        return True
    a, m, d = iso.split("-")
    if f"{int(d)}/{int(m)}/{a}" in texto or f"{d}/{m}/{a}" in texto:
        return True
    mes = next(k for k, v in MESES.items() if v == int(m))
    return re.search(rf"\b{int(d)} de {mes}\b", texto, re.I) is not None


def _contiene_str(texto: str, s: str) -> bool:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return _contiene_fecha(texto, s)
    return s.lower() in texto.lower()


def evaluar(p: dict, d: dict) -> tuple[bool, str]:
    """p: pregunta del golden set; d: respuesta del orquestador (a_dict)."""
    texto, tipo, esp, tp = d["respuesta"], d["tipo"], p["respuesta_esperada"], p["tipo"]
    if tp == "rechazo":
        return tipo == "RECHAZO", f"tipo={tipo}"
    if tp == "fuera_dominio":
        return tipo in ("FUERA_DOMINIO", "RECHAZO"), f"tipo={tipo}"
    if tp == "sin_datos":
        return tipo == "SIN_DATOS" or bool(RE_NO_HAY.search(texto)), f"tipo={tipo}"
    if tipo in ("SIN_DATOS", "FUERA_DOMINIO", "RECHAZO"):
        return False, f"falso «no sé» (tipo={tipo})"
    tol = p.get("tolerancia_pct")
    if tp == "entero":
        if esp == 0:
            return bool(RE_CERO.search(texto)), "espera 0 / ninguna"
        return _contiene_num(texto, esp, None, entero=True), f"espera {esp}"
    if tp == "decimal":
        if "puntos" in (p.get("nota") or ""):
            return any(abs(v - esp) <= tol for v in _valores(texto)), f"espera {esp} ± {tol} pp"
        return _contiene_num(texto, esp, tol), f"espera {esp} ± {tol or 0.5}%"
    if tp == "texto":
        return _contiene_str(texto, esp), f"espera «{esp}»"
    if tp == "lista":
        faltan = [x for x in esp if not _contiene_str(texto, x)]
        if faltan:
            return False, f"faltan {len(faltan)} de {len(esp)}: {', '.join(faltan[:3])}"
        if p.get("comparacion") == "ordenada":
            pos = [texto.lower().find(x.lower()) for x in esp]
            return pos == sorted(pos), "orden correcto" if pos == sorted(pos) else "orden incorrecto"
        return True, f"{len(esp)} de {len(esp)}"
    if tp == "objeto":
        malos = []
        for k, v in esp.items():
            ok = (_contiene_num(texto, v, tol) if isinstance(v, (int, float)) else
                  all(_contiene_str(texto, x) for x in v) if isinstance(v, list) else _contiene_str(texto, str(v)))
            if not ok:
                malos.append(k)
        return not malos, "completo" if not malos else f"falta: {', '.join(malos)}"
    return False, f"tipo no soportado: {tp}"
