#!/usr/bin/env python3
"""
Guardia de confidencialidad: impide publicar datos reales en el repositorio.

Revisa los archivos versionados (git ls-files) o, fuera de git, el árbol del
proyecto, y falla (exit 1) si encuentra:
  1. OCIDs con formato real (los sintéticos llevan el marcador "synth").
  2. Palabras prohibidas: nombres de clientes, empleadores, dominios, etc.
     La lista NO se guarda en el repo (publicarla ya sería una filtración):
       - localmente: archivo .confidencial.txt (una palabra por línea, en .gitignore)
       - en CI: secreto de GitHub PALABRAS_PROHIBIDAS (separadas por comas)
  3. Tipos de archivo que no deben versionarse (hojas de cálculo, bases de datos,
     llaves y videos).

Uso:  python scripts/verificar_confidencialidad.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_PROHIBIDAS = {".xlsx", ".xls", ".sqlite", ".sqlite3", ".db", ".pem", ".key", ".p12", ".pfx",
                  ".mp4", ".mov", ".mkv", ".avi"}
EXCLUIR_DIRS = {".git", "node_modules", ".venv", "venv", "data", "__pycache__", ".pytest_cache"}
# OCID real: ocid1.<tipo>.oc1.<region?>.<id> cuyo id NO empieza con "synth"
RE_OCID_REAL = re.compile(r"ocid1\.[a-z0-9]+\.oc[0-9]\.[a-z0-9-]*\.(?!synth)[a-z0-9]{20,}", re.I)
EXT_TEXTO = {".py", ".md", ".txt", ".json", ".csv", ".yml", ".yaml", ".js", ".jsx", ".ts", ".tsx",
             ".html", ".css", ".toml", ".ini", ".cfg", ".env", ".example", ".sh", ".ps1", ""}


def archivos() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=RAIZ,
                             capture_output=True, text=True, check=True).stdout
        return [f for f in out.splitlines() if f]
    except (subprocess.CalledProcessError, FileNotFoundError):
        res = []
        for base, dirs, fs in os.walk(RAIZ):
            dirs[:] = [d for d in dirs if d not in EXCLUIR_DIRS]
            res += [os.path.relpath(os.path.join(base, f), RAIZ) for f in fs]
        return res


def palabras() -> list[str]:
    ws = [w.strip() for w in os.environ.get("PALABRAS_PROHIBIDAS", "").split(",")]
    ruta = os.path.join(RAIZ, ".confidencial.txt")
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            ws += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    return sorted({w.lower() for w in ws if w})


def main() -> int:
    ws = palabras()
    re_ws = re.compile("|".join(re.escape(w) for w in ws), re.I) if ws else None
    hallazgos = []
    for rel in archivos():
        ext = os.path.splitext(rel)[1].lower()
        if ext in EXT_PROHIBIDAS:
            hallazgos.append(f"{rel}: tipo de archivo no permitido en el repo ({ext})")
            continue
        if ext not in EXT_TEXTO or rel.endswith("verificar_confidencialidad.py") or os.path.basename(rel) == ".confidencial.txt":
            continue
        try:
            with open(os.path.join(RAIZ, rel), encoding="utf-8", errors="ignore") as f:
                for n, linea in enumerate(f, 1):
                    if RE_OCID_REAL.search(linea):
                        hallazgos.append(f"{rel}:{n}: OCID con formato real (no sintético)")
                    if re_ws:
                        m = re_ws.search(linea)
                        if m:
                            hallazgos.append(f"{rel}:{n}: palabra prohibida «{m.group(0)}»")
        except OSError:
            continue
    if not ws:
        print("Aviso: no hay palabras prohibidas configuradas (.confidencial.txt o PALABRAS_PROHIBIDAS).")
    if hallazgos:
        print("Confidencialidad: se encontraron problemas:")
        print("\n".join(f"  - {h}" for h in hallazgos))
        return 1
    print(f"Confidencialidad OK ({len(ws)} palabras vigiladas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
