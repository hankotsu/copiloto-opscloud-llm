"""
Heurística anti-alucinación propia: VERIFICADOR DE PROCEDENCIA.

La heurística de clase (Sesión 4) busca patrones sospechosos con regex. Esta
verifica DE DÓNDE sale cada dato de la respuesta:

  Capa 1  · Procedencia: cada cifra, fecha y nombre de recurso debe existir en
            los resultados de las tools del turno (o en la pregunta / contexto).
  Capa 1b · Coherencia cifra–recurso: si una frase asocia UNA cifra a UN recurso,
            ambos deben aparecer en la misma fila de un resultado.
  Capa 2  · Afirmación sin evidencia: hay cifras o recursos y no se llamó a
            ninguna tool (el caso típico del modo sin grounding).
  Capa 3  · Derivados verificables: si una cifra no aparece literal, se intenta
            reconstruir con dos valores de la evidencia (suma, diferencia,
            cociente, variación %) o con la suma de una columna.

Veredictos: VERIFICADA · PARCIAL · NO_VERIFICADA · SIN_CIFRAS
"""
from __future__ import annotations

import itertools
import json
import re
from dataclasses import asdict, dataclass, field

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
         "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}

# Entidades (nombres de recursos) según las convenciones del tenancy
RE_ENTIDAD = re.compile(
    r"\b[A-Z]{3}-[A-Z]{3}-(?:PRD|QA|DEV)-[A-Z]+(?:-\d{3})?(?:-DATA-\w+)?(?: \(Boot Volume\))?"
    r"|\b(?:ade|sl|vcn|lb|igw|fc|vol|sn)-[a-z0-9]+(?:-[a-z0-9]+)+\b"
    r"|\bprueba-fra-vm\b")
RE_IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?\b")
RE_RUIDO = re.compile(
    r"\b(?:sa-saopaulo-1|sa-vinhedo-1|sa-santiago-1|eu-frankfurt-1|us-[a-z]+-\d)\b"   # regiones
    r"|\b(?:VM|BM)\.[A-Za-z0-9.]+"                                                    # shapes
    r"|ocid1\.[\w.-]+|\bFAULT-DOMAIN-\d\b|\bAD-\d\b|\bG\d{2}\b|\bI\d{2}\b|\bA\d\b"      # ids
    r"|\bOWASP\b|\bLLM\d{2}\b|\b(?:top|Top|TOP)[\s-]?\d+\b")
RE_FECHA_ISO = re.compile(r"\b(\d{4})-(\d{2})(?:-(\d{2}))?\b")
RE_FECHA_DMY = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
RE_FECHA_TXT = re.compile(r"\b(?:(\d{1,2}) de )?(" + "|".join(MESES) + r")(?: (?:de|del) )?(\d{4})?\b", re.I)
RE_LISTA = re.compile(r"(?m)^\s*(?:[-*•]|\d{1,2}[.)])\s+")
RE_NUM = re.compile(
    r"(?<![\w/])(?:USD|US\$|\$)?\s?(\d{1,3}(?:[.,  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"(\s?%|\s?(?:mil\b|millones?\b|[kK]\b))?")
# Cláusulas: la capa 1b solo asocia una cifra al recurso de SU cláusula
RE_SEGMENTOS = re.compile(r"\n+|(?<=[.:!?])\s+(?=[A-ZÁÉÍÓÚ¿¡•\-*])|;\s*|,\s+|\s+y\s+(?=[A-Z]{3}-)")


@dataclass
class Afirmacion:
    tipo: str            # cifra | recurso | fecha
    texto: str
    valor: object
    estado: str          # respaldada | derivada | del_usuario | no_respaldada | atribucion_dudosa
    detalle: str = ""
    segmento: int = 0


@dataclass
class Resultado:
    veredicto: str
    afirmaciones: list[Afirmacion] = field(default_factory=list)
    capas: list[str] = field(default_factory=list)
    resumen: str = ""

    def a_dict(self):
        return {"veredicto": self.veredicto, "resumen": self.resumen, "capas_disparadas": self.capas,
                "afirmaciones": [asdict(a) for a in self.afirmaciones]}


# ─────────────────────────────── extracción de números
def candidatos(s: str) -> list[tuple[float, float]]:
    """Interpretaciones posibles de un número escrito (valor, unidad de redondeo).
    Maneja 65,725.46 · 65.725,46 · 65 725 · 1.500 (ambiguo: 1500 o 1,5)."""
    s = s.replace(" ", ",").replace(" ", ",")
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        mil = "." if dec == "," else ","
        ent, frac = s.replace(mil, "").split(dec)
        return [(float(f"{ent}.{frac}"), 10 ** -len(frac))]
    for sep in (",", "."):
        if sep in s:
            partes = s.split(sep)
            if len(partes) > 2:
                return [(float("".join(partes)), 1.0)]
            ent, frac = partes
            if len(frac) == 3:  # ambiguo
                return [(float(ent + frac), 1.0), (float(f"{ent}.{frac}"), 0.001)]
            return [(float(f"{ent}.{frac}"), 10 ** -len(frac))]
    return [(float(s), 1.0)]


def extraer_numeros(texto: str) -> list[dict]:
    out = []
    for m in RE_NUM.finditer(texto):
        suf = (m.group(2) or "").strip().lower()
        mult = 1e6 if suf.startswith("millon") else 1e3 if suf in ("mil", "k") else 1
        cands = [(v * mult, u * mult) for v, u in candidatos(m.group(1))]
        out.append({"texto": m.group(0).strip(), "cands": cands, "pct": suf == "%"})
    return out


def _numeros_en(obj, acc: list, filas: list, texto_libre=True):
    """Recorre un resultado de tool: valores numéricos, números dentro de strings,
    largos de listas y sumas por columna; guarda las 'filas' para la capa 1b."""
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        acc.append(float(obj))
    elif isinstance(obj, str):
        if texto_libre:
            for n in extraer_numeros(RE_RUIDO.sub(" ", obj)):
                acc.extend(v for v, _ in n["cands"])
    elif isinstance(obj, dict):
        if any(isinstance(v, str) for v in obj.values()) and any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in obj.values()):
            filas.append(obj)
        for v in obj.values():
            _numeros_en(v, acc, filas, texto_libre)
    elif isinstance(obj, list):
        acc.append(float(len(obj)))
        if obj and all(isinstance(x, dict) for x in obj):
            for k in obj[0]:
                vals = [x.get(k) for x in obj]
                if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
                    acc.append(float(sum(vals)))
        for x in obj:
            _numeros_en(x, acc, filas, texto_libre)


def _coincide(v: float, u: float, evidencia, rel=0.001) -> bool:
    for e in evidencia:
        if abs(e - v) <= u / 2 + 1e-9 or (e and abs(e - v) <= abs(e) * rel):
            return True
    return False


def _derivable(v: float, u: float, evidencia: list[float]) -> str | None:
    base = sorted({e for e in evidencia if abs(e) >= 1}, key=abs, reverse=True)[:120]
    for a, b in itertools.permutations(base, 2):
        for nombre, r in (("a+b", a + b), ("a-b", a - b), ("a/b·100", a / b * 100 if b else None),
                          ("(a-b)/b·100", (a - b) / b * 100 if b else None), ("a/b", a / b if b else None)):
            if r is not None and abs(r - v) <= max(u / 2, abs(v) * 0.001) + 1e-9:
                return f"{nombre} con a={a:g}, b={b:g}"
    return None


# ─────────────────────────────── fechas
def _fechas(texto: str) -> tuple[list[tuple[str, str]], str]:
    encontradas = []

    def iso(m):
        encontradas.append((m.group(0), m.group(0)))
        return " ⟦F⟧ "

    def dmy(m):
        d, mes, a = m.groups()
        encontradas.append((m.group(0), f"{a}-{int(mes):02d}-{int(d):02d}"))
        return " ⟦F⟧ "

    def txt(m):
        d, mes, a = m.group(1), MESES[m.group(2).lower()], m.group(3)
        if not a:
            encontradas.append((m.group(0), f"-{mes:02d}" + (f"-{int(d):02d}" if d else "")))
        else:
            encontradas.append((m.group(0), f"{a}-{mes:02d}" + (f"-{int(d):02d}" if d else "")))
        return " ⟦F⟧ "

    texto = RE_FECHA_ISO.sub(iso, texto)
    texto = RE_FECHA_DMY.sub(dmy, texto)
    texto = RE_FECHA_TXT.sub(txt, texto)
    return encontradas, texto


# ─────────────────────────────── verificación
def verificar(respuesta: str, resultados_tools: list[dict], pregunta: str = "", contexto: str = "") -> Resultado:
    evid_texto = json.dumps(resultados_tools, ensure_ascii=False) + " " + contexto
    evidencia, filas = [], []
    for r in resultados_tools:
        _numeros_en(r, evidencia, filas)
    _numeros_en(contexto, evidencia, [])
    usuario = []
    for n in extraer_numeros(RE_RUIDO.sub(" ", _fechas(pregunta)[1])):
        usuario.extend(v for v, _ in n["cands"])
    fechas_usuario = {f for _, f in _fechas(pregunta)[0]}

    texto = respuesta.replace("**", "").replace("`", "")
    texto = RE_LISTA.sub("", texto)
    afirmaciones: list[Afirmacion] = []
    for i, seg in enumerate(s for s in RE_SEGMENTOS.split(texto) if s.strip()):
        # Entidades
        for m in RE_ENTIDAD.finditer(seg):
            nombre = m.group(0)
            if nombre in evid_texto:
                est = "respaldada"
            elif nombre in pregunta:
                est = "del_usuario"
            else:
                est = "no_respaldada"
            afirmaciones.append(Afirmacion("recurso", nombre, nombre, est, "" if est != "no_respaldada" else "recurso no presente en los resultados", i))
        seg_limpio = RE_ENTIDAD.sub(" ⟦E⟧ ", seg)
        for m in RE_IP.finditer(seg_limpio):
            est = "respaldada" if m.group(0) in evid_texto else "no_respaldada"
            afirmaciones.append(Afirmacion("recurso", m.group(0), m.group(0), est, "", i))
        seg_limpio = RE_IP.sub(" ⟦E⟧ ", seg_limpio)
        # Fechas
        fechas, seg_limpio = _fechas(seg_limpio)
        for original, norm in fechas:
            if norm.startswith("-"):
                continue  # mes sin año ("en agosto"): no es una afirmación verificable
            if norm in fechas_usuario:  # repetir la fecha de la pregunta no es una afirmación nueva
                afirmaciones.append(Afirmacion("fecha", original, norm, "del_usuario", "", i))
                continue
            ok = norm in evid_texto
            afirmaciones.append(Afirmacion("fecha", original, norm, "respaldada" if ok else "no_respaldada", "", i))
        # Cifras
        seg_limpio = RE_RUIDO.sub(" ", seg_limpio)
        for n in extraer_numeros(seg_limpio):
            if any(_coincide(v, u, usuario) for v, u in n["cands"]) and not any(_coincide(v, u, evidencia) for v, u in n["cands"]):
                afirmaciones.append(Afirmacion("cifra", n["texto"], n["cands"][0][0], "del_usuario", "", i))
                continue
            if any(_coincide(v, u, evidencia) for v, u in n["cands"]):
                afirmaciones.append(Afirmacion("cifra", n["texto"], n["cands"][0][0], "respaldada", "", i))
                continue
            deriv = next((d for v, u in n["cands"] if (d := _derivable(v, u, evidencia))), None) if resultados_tools else None
            afirmaciones.append(Afirmacion("cifra", n["texto"], n["cands"][0][0], "derivada" if deriv else "no_respaldada",
                                           deriv or "no aparece en los resultados de las herramientas", i))

    capas = set()
    # Capa 2: afirmaciones sin ninguna llamada a herramientas
    if not resultados_tools:
        for a in afirmaciones:
            if a.estado != "del_usuario" and not (a.estado == "respaldada" and contexto and str(a.texto) in contexto):
                a.estado, a.detalle = "no_respaldada", "afirmación sin llamadas a herramientas (sin evidencia)"
                capas.add("2")
    # Capa 1b: cifra real atribuida al recurso equivocado
    for seg_id in {a.segmento for a in afirmaciones}:
        ents = [a for a in afirmaciones if a.segmento == seg_id and a.tipo == "recurso" and a.estado == "respaldada"]
        nums = [a for a in afirmaciones if a.segmento == seg_id and a.tipo == "cifra" and a.estado == "respaldada"
                and (abs(a.valor) >= 13 or a.valor != int(a.valor))]
        if len({e.texto for e in ents}) != 1 or not nums:
            continue
        # filas donde el recurso es un valor DIRECTO (no un dict que lo contiene más abajo)
        propias = [f for f in filas if any(isinstance(v, str) and ents[0].texto in v for v in f.values())]
        if not propias:
            continue
        vals = [float(v) for f in propias for v in f.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        for a in nums:
            cands = next((n["cands"] for n in extraer_numeros(a.texto)), [(a.valor, 0.01)])
            if not any(_coincide(v, u, vals) for v, u in cands):
                a.estado = "atribucion_dudosa"
                a.detalle = f"la cifra existe en los resultados, pero no en la fila de {ents[0].texto}"
                capas.add("1b")
    for a in afirmaciones:
        if a.estado == "no_respaldada" and "2" not in capas:
            capas.add("1")
        if a.estado == "derivada":
            capas.add("3")

    malas = [a for a in afirmaciones if a.estado in ("no_respaldada", "atribucion_dudosa")]
    evaluables = [a for a in afirmaciones if a.estado != "del_usuario"]
    if not evaluables:
        v = "SIN_CIFRAS"
    elif not malas:
        v = "VERIFICADA"
    elif len(malas) < len(evaluables):
        v = "PARCIAL"
    else:
        v = "NO_VERIFICADA"
    resumen = (f"{len(evaluables) - len(malas)} de {len(evaluables)} afirmaciones con respaldo" if evaluables
               else "La respuesta no contiene cifras, fechas ni recursos que verificar")
    return Resultado(v, afirmaciones, sorted(capas), resumen)
