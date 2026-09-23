#!/usr/bin/env python3
"""
Diagnóstico rápido de un proveedor: ¿responde?, ¿llama a las tools?, ¿cuánto demora?

Uso (desde la raíz del repo):
  python scripts/probar_proveedor.py --proveedor ollama
  python scripts/probar_proveedor.py --proveedor gemini --pregunta "¿Qué buckets tienen acceso público?"
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows: permite redirigir la salida a un archivo
from backend.orquestador import Orquestador  # noqa: E402
from backend.proveedores import ErrorProveedor, crear_proveedor  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--proveedor", default="ollama", choices=["ollama", "gemini", "openai", "simulado"])
ap.add_argument("--pregunta", default="¿Cuál fue el costo total del tenancy en agosto de 2026?")
a = ap.parse_args()

prov = crear_proveedor(a.proveedor)
print(f"Proveedor: {prov.nombre} · modelo: {prov.modelo}{' · SIMULADO (falta la API key o MODO_SIMULADO=true)' if prov.modo_simulado and a.proveedor != 'simulado' else ''}")
o = Orquestador(prov)
for grounding in (True, False):
    print(f"\n── {'CON' if grounding else 'SIN'} grounding ─────────────────────────────")
    try:
        r = o.responder(a.pregunta, grounding)
    except ErrorProveedor as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    for p in r.pasos:
        print(f"  tool: {p.tool}({json.dumps(p.argumentos, ensure_ascii=False)}) → {'ok' if p.ok else 'ERROR: ' + p.error}")
    print(f"  respuesta [{r.tipo}]: {r.respuesta}")
    print(f"  verificador: {r.verificacion['veredicto']} · {r.verificacion['resumen']}")
    print(f"  {r.tokens_entrada}+{r.tokens_salida} tokens · {r.latencia_s}s · {r.iteraciones} iteración(es)")
    if grounding and not r.pasos and r.tipo == "RESPUESTA":
        print("  ⚠ El modelo NO llamó a ninguna herramienta. Verifique que el modelo soporte tools "
              "(ollama show <modelo> → Capabilities: tools) y que OLLAMA_NUM_CTX sea ≥ 8192.")
