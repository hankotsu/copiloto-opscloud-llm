"""
Re-verificación OFFLINE de respuestas guardadas (medir ANTES y DESPUÉS de un ajuste del verificador).

En modo SIN grounding el verificador solo depende de (respuesta, pregunta): no hay tools ni contexto, así que
se puede reproducir exactamente sin llamar a ningún modelo. Las filas CON grounding no se re-verifican aquí
(los resultados de las tools no se guardan en respuestas.jsonl): se miden volviendo a correr run_eval.py.

Uso:  python eval/reverificar.py eval/resultados/<corrida> [<corrida> ...]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.config import CONFIG  # noqa: E402
from backend.verificador import verificar  # noqa: E402

ALERTA = ("PARCIAL", "NO_VERIFICADA")


def main(rutas):
    base = CONFIG.db_path.parent / "eval"
    preguntas = {p["id"]: p["pregunta"] for p in json.loads((base / "golden_set.json").read_text(encoding="utf-8"))["preguntas"]}
    for ruta in rutas:
        filas = [json.loads(x) for x in open(os.path.join(ruta, "respuestas.jsonl"), encoding="utf-8")]
        sin = [f for f in filas if not f["grounding"] and f["tipo"] != "ERROR" and f["id"] in preguntas]
        print(f"\n== {os.path.basename(ruta.rstrip('/\\\\'))} · {len(sin)} respuestas SIN grounding ==")
        cambios = 0
        for f in sin:
            f["antes"] = f["veredicto"]
            f["despues"] = verificar(f["respuesta"], [], preguntas[f["id"]], "").veredicto
            if f["antes"] != f["despues"]:
                cambios += 1
                print(f"  {f['id']}: {f['antes']} → {f['despues']}  (correcta={f['correcta']})")
        print(f"  Veredictos cambiados: {cambios}")
        for etiqueta, clave in (("ANTES", "antes"), ("DESPUÉS", "despues")):
            incorrectas = [f for f in sin if not f["correcta"]]
            alertadas = sum(1 for f in incorrectas if f[clave] in ALERTA)
            falsas = sum(1 for f in sin if f[clave] in ALERTA and f["correcta"])
            con_cifras = [f for f in sin if f[clave] != "SIN_CIFRAS"]
            print(f"  {etiqueta}: alertas={sum(1 for f in sin if f[clave] in ALERTA)} · incorrectas alertadas={alertadas}/{len(incorrectas)}"
                  f" · falsas alertas={falsas} · respuestas con cifras={len(con_cifras)}")


if __name__ == "__main__":
    main(sys.argv[1:])
