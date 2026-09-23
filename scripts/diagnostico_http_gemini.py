"""Diagnóstico HTTP directo de Gemini, sin pasar por el adaptador del backend.

Sirve para demostrar el origen de un error (503, 429, 401/403, 404):
  1. GET /models          -> valida la key y la disponibilidad del modelo (no consume cuota de generación).
  2. POST chat/completions -> UNA llamada mínima; muestra el cuerpo del error tal como lo devuelve Google.

La API key se lee de la variable de entorno o de .env, se envía por cabecera (nunca en la URL)
y se enmascara en toda la salida.

Uso:
  python scripts/diagnostico_http_gemini.py --salida docs/evidencias/diagnostico_http_gemini.txt
"""
import argparse
import datetime
import json
import os
import pathlib
import time

import httpx

BASE = "https://generativelanguage.googleapis.com/v1beta"


def leer_env(ruta: str = ".env") -> dict:
    valores = {}
    p = pathlib.Path(ruta)
    if p.exists():
        for linea in p.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip().strip('"').strip("'")
    return valores


def config(nombre: str, env: dict, defecto: str = "") -> str:
    return os.environ.get(nombre) or env.get(nombre) or defecto


def cuerpo_json(resp: httpx.Response):
    try:
        return resp.json()
    except ValueError:
        return resp.text


def detalle_error(cuerpo) -> list[str]:
    """Extrae status, mensaje y (en 429) la cuota agotada y el tiempo de espera sugerido."""
    lineas = []
    if isinstance(cuerpo, list) and cuerpo:
        cuerpo = cuerpo[0]
    if not isinstance(cuerpo, dict):
        return lineas
    err = cuerpo.get("error", cuerpo)
    if not isinstance(err, dict):
        return lineas
    for campo in ("code", "status", "message"):
        if campo in err:
            lineas.append(f"  error.{campo}: {err[campo]}")
    for d in err.get("details", []) or []:
        if not isinstance(d, dict):
            continue
        for v in d.get("violations", []) or []:
            lineas.append(
                f"  cuota: {v.get('quotaId', '')} · métrica: {v.get('quotaMetric', '')} · valor: {v.get('quotaValue', '')}"
            )
        if "retryDelay" in d:
            lineas.append(f"  retryDelay sugerido: {d['retryDelay']}")
    return lineas


def interpretar(codigo_modelos: int, modelo_listado: bool, codigo_chat: int) -> str:
    if codigo_modelos in (401, 403) or codigo_chat in (401, 403):
        return "Problema de autenticación: revisar la API key en .env."
    if codigo_modelos == 200 and not modelo_listado:
        return "La key es válida pero el modelo no aparece en la lista: modelo retirado o no disponible para la cuenta."
    if codigo_chat == 200:
        return "Servicio operativo: la key y el modelo responden correctamente."
    if codigo_chat == 503:
        return ("Key válida y modelo disponible; el 503 lo emite Google (servicio saturado). "
                "No es un fallo del sistema ni de la configuración.")
    if codigo_chat == 429:
        return ("Cuota de la capa gratuita agotada. Revisar arriba si la cuota es por minuto "
                "(esperar y usar --pausa) o por día (esperar al reinicio diario).")
    if codigo_chat == 404:
        return "Modelo no encontrado en el endpoint de chat."
    return f"Resultado no previsto (models={codigo_modelos}, chat={codigo_chat})."


def main() -> None:
    ap = argparse.ArgumentParser(description="Diagnóstico HTTP directo de Gemini")
    ap.add_argument("--salida", help="Archivo de salida (UTF-8)")
    args = ap.parse_args()

    env = leer_env()
    key = config("GEMINI_API_KEY", env)
    modelo = config("GEMINI_MODEL", env, "gemini-3.5-flash")
    salida: list[str] = []

    def out(texto: str = "") -> None:
        if key:
            texto = texto.replace(key, "***")
        print(texto)
        salida.append(texto)

    ahora = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    out(f"Diagnóstico HTTP directo de Gemini · {ahora}")
    out(f"Modelo: {modelo} · endpoint: {BASE}")
    out()

    if not key:
        out("ERROR: no hay GEMINI_API_KEY en el entorno ni en .env")
        return

    cabeceras = {"x-goog-api-key": key}
    codigo_modelos, modelo_listado, codigo_chat = 0, False, 0

    with httpx.Client(timeout=60) as cli:
        # 1. Listado de modelos (no consume cuota de generación)
        out("── 1. GET /models ─────────────────────────────")
        try:
            r = cli.get(f"{BASE}/models", headers=cabeceras, params={"pageSize": 1000})
            codigo_modelos = r.status_code
            out(f"HTTP {r.status_code}")
            cuerpo = cuerpo_json(r)
            if r.status_code == 200 and isinstance(cuerpo, dict):
                nombres = [m.get("name", "") for m in cuerpo.get("models", [])]
                modelo_listado = f"models/{modelo}" in nombres
                out(f"  modelos visibles para la key: {len(nombres)}")
                out(f"  models/{modelo} disponible: {'sí' if modelo_listado else 'NO'}")
            else:
                for linea in detalle_error(cuerpo):
                    out(linea)
        except httpx.HTTPError as e:
            out(f"  error de red: {type(e).__name__}")
        out()

        # 2. Una llamada mínima de chat
        out("── 2. POST /openai/chat/completions (1 llamada) ─")
        payload = {
            "model": modelo,
            "messages": [{"role": "user", "content": "Responde solo con la palabra OK."}],
            "max_tokens": 50,
            "temperature": 0,
        }
        try:
            t0 = time.perf_counter()
            r = cli.post(f"{BASE}/openai/chat/completions",
                         headers={**cabeceras, "Authorization": f"Bearer {key}"}, json=payload)
            dt = time.perf_counter() - t0
            codigo_chat = r.status_code
            out(f"HTTP {r.status_code} · {dt:.1f} s")
            for h in ("retry-after", "x-goog-request-id"):
                if h in r.headers:
                    out(f"  {h}: {r.headers[h]}")
            cuerpo = cuerpo_json(r)
            if r.status_code == 200 and isinstance(cuerpo, dict):
                texto = (cuerpo.get("choices") or [{}])[0].get("message", {}).get("content")
                out(f"  respuesta: {texto!r}")
            else:
                for linea in detalle_error(cuerpo):
                    out(linea)
                out("  cuerpo crudo (recortado):")
                crudo = json.dumps(cuerpo, ensure_ascii=False, indent=1) if not isinstance(cuerpo, str) else cuerpo
                out(crudo[:1500])
        except httpx.HTTPError as e:
            out(f"  error de red: {type(e).__name__}")
        out()

    out("── Interpretación ──────────────────────────────")
    out(interpretar(codigo_modelos, modelo_listado, codigo_chat))

    if args.salida:
        pathlib.Path(args.salida).write_text("\n".join(salida) + "\n", encoding="utf-8")
        print(f"\nGuardado en {args.salida}")


if __name__ == "__main__":
    main()
