"""
Recuperación: tools de SOLO LECTURA sobre la base SQLite sintética.

Cada tool:
  * valida sus argumentos con un modelo Pydantic (lo que el LLM envía nunca se
    usa sin validar; los valores van como parámetros SQL, nunca concatenados);
  * devuelve solo las filas relevantes (máximo MAX_FILAS) y los agregados
    calculados por SQL: el LLM no necesita sumar ni contar;
  * marca como "_no_confiable" el texto libre que escriben usuarios de la nube
    (tags, descripciones), porque puede contener instrucciones maliciosas.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .config import CONFIG

MAX_FILAS = CONFIG.max_filas_tool  # filas máximas por resultado (evita inyectar la base completa)
Ambiente = Literal["PRD", "QA", "DEV"]
MES = r"^\d{4}-(0[1-9]|1[0-2])$"
REGION = r"^[a-z]{2}-[a-z]+-\d$"


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ─────────────────────────────── modelos de argumentos
class ArgsInstancias(_Args):
    region: Optional[str] = Field(None, pattern=REGION, description="Región OCI, ej. sa-saopaulo-1")
    ambiente: Optional[Ambiente] = Field(None, description="PRD (producción), QA o DEV")
    estado: Optional[Literal["RUNNING", "STOPPED"]] = None
    sistema_operativo: Optional[Literal["Windows", "Oracle Linux", "Ubuntu"]] = None
    creadas_desde: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Fecha YYYY-MM-DD")
    nombre_contiene: Optional[str] = Field(None, max_length=40)


class ArgsVacios(_Args):
    pass


class ArgsCobertura(_Args):
    ambiente: Optional[Ambiente] = None
    region: Optional[str] = Field(None, pattern=REGION)
    estado_respaldo: Optional[Literal["PROTEGIDO", "ATENCION", "SIN RESPALDO"]] = None
    con_politica: Optional[bool] = Field(None, description="true: solo discos con política asignada; false: solo sin política")
    instancia: Optional[str] = Field(None, max_length=40)


class ArgsBD(_Args):
    ambiente: Optional[Ambiente] = None
    auto_backup: Optional[bool] = Field(None, description="false: solo las que tienen el respaldo automático deshabilitado")
    version_menor_a: Optional[str] = Field(None, pattern=r"^\d{2}\.\d{1,2}$", description="Ej. 19.27")


class ArgsHuerfanos(_Args):
    tipo: Literal["volumenes", "backups"]
    mes: Optional[str] = Field(None, pattern=MES, description="Mes para el costo, YYYY-MM (por defecto el último)")


class ArgsCostos(_Args):
    mes: str = Field(..., pattern=MES, description="Mes YYYY-MM")
    agrupar_por: Literal["total", "region", "servicio", "recurso", "dia"] = "total"
    region: Optional[str] = Field(None, pattern=REGION)
    servicio: Optional[Literal["Compute", "Block Storage", "Database", "Object Storage", "Load Balancer", "Networking"]] = None
    sku_contiene: Optional[str] = Field(None, max_length=40, description="Ej. 'Outbound Data Transfer'")
    recursos: Optional[list[str]] = Field(None, max_length=50, description="Nombres de recursos a incluir")
    top: int = Field(10, ge=1, le=MAX_FILAS)


class ArgsVariacion(_Args):
    tipo: Literal["meses", "recursos"]
    mes_a: Optional[str] = Field(None, pattern=MES, description="Mes base (tipo=meses)")
    mes_b: Optional[str] = Field(None, pattern=MES, description="Mes comparado (tipo=meses)")
    dias: int = Field(14, ge=1, le=45, description="Ventana en días (tipo=recursos)")
    top: int = Field(5, ge=1, le=MAX_FILAS)


class ArgsMes(_Args):
    mes: str = Field(..., pattern=MES)


class ArgsReglas(_Args):
    security_list: Optional[str] = Field(None, max_length=60)
    puerto: Optional[int] = Field(None, ge=0, le=65535)
    solo_publicas: bool = Field(False, description="true: solo reglas con origen 0.0.0.0/0")
    excluir_web_balanceador: bool = Field(False, description="true: excluye 80/443 en listas de balanceador")


class ArgsBuckets(_Args):
    publicos: Optional[bool] = None
    tier: Optional[Literal["Standard", "InfrequentAccess", "Archive"]] = None
    min_gb: Optional[float] = Field(None, ge=0)
    sin_ciclo_vida: Optional[bool] = None


class ArgsDetalle(_Args):
    nombre: str = Field(..., min_length=3, max_length=80, description="Nombre exacto del recurso")


# ─────────────────────────────── utilidades
def conectar(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)  # solo lectura
    con.row_factory = sqlite3.Row
    return con


def _filas(con, sql, params=()):
    return [dict(r) for r in con.execute(sql, params).fetchall()]


def _where(conds: list[tuple[str, Any]]):
    partes, params = [], []
    for sql, val in conds:
        if val is not None:
            partes.append(sql)
            params.append(val)
    return (" WHERE " + " AND ".join(partes)) if partes else "", params


def _r(x, n=2):
    return round(x, n) if isinstance(x, float) else x


def _limitar(filas, n=MAX_FILAS):
    return {"filas": filas[:n], "filas_devueltas": min(len(filas), n), "filas_totales": len(filas),
            "truncado": len(filas) > n}


def periodo(con) -> dict:
    a, b = con.execute("SELECT min(fecha), max(fecha) FROM costos_diarios").fetchone()
    return {"desde": a, "hasta": b}


def _mes_valido(con, mes):
    p = periodo(con)
    return p["desde"][:7] <= mes <= p["hasta"][:7], p


def _no_confiable(texto: str):
    return {"_no_confiable": texto} if texto else texto


# ─────────────────────────────── tools
def consultar_instancias(con, a: ArgsInstancias):
    where, params = _where([("region = ?", a.region), ("ambiente = ?", a.ambiente), ("estado = ?", a.estado),
                            ("sistema_operativo = ?", a.sistema_operativo),
                            ("substr(creado,1,10) >= ?", a.creadas_desde),
                            ("nombre LIKE ?", f"%{a.nombre_contiene}%" if a.nombre_contiene else None)])
    filas = _filas(con, f"""SELECT nombre, region, ambiente, estado, shape, ocpus, memoria_gb, sistema_operativo,
                            substr(creado,1,10) AS creado FROM instancias{where} ORDER BY nombre""", params)
    por_region = {}
    for f in filas:
        por_region[f["region"]] = por_region.get(f["region"], 0) + 1
    return {"total_instancias": len(filas), "ocpus_total": sum(f["ocpus"] for f in filas),
            "memoria_total_gb": sum(f["memoria_gb"] for f in filas), "por_region": por_region, **_limitar(filas)}


def cumplimiento_etiquetado(con, a: ArgsVacios):
    tot = con.execute("SELECT count(*) FROM instancias").fetchone()[0]
    inc = [r[0] for r in con.execute("SELECT nombre FROM instancias WHERE etiquetado_completo='No' ORDER BY nombre")]
    return {"total_instancias": tot, "con_etiquetado_completo": tot - len(inc),
            "porcentaje_cumplimiento": round(100 * (tot - len(inc)) / tot, 1),
            "tags_obligatorios": ["Empresa", "Aplicacion", "Ambiente", "CentroCosto"],
            "instancias_incompletas": inc[:MAX_FILAS], "incompletas_totales": len(inc)}


def cobertura_respaldo(con, a: ArgsCobertura):
    conds = [("ambiente = ?", a.ambiente), ("region = ?", a.region), ("estado_respaldo = ?", a.estado_respaldo),
             ("instancia LIKE ?", f"%{a.instancia}%" if a.instancia else None)]
    where, params = _where(conds)
    if a.con_politica is not None:
        where += (" AND " if where else " WHERE ") + ("politica_backup IS NOT NULL" if a.con_politica else "politica_backup IS NULL")
    filas = _filas(con, f"""SELECT nombre AS disco, tipo_volumen, instancia, ambiente, region, politica_backup,
                            ultimo_backup, antiguedad_dias, estado_respaldo FROM cobertura_discos{where}
                            ORDER BY estado_respaldo DESC, nombre""", params)
    resumen = {}
    for f in filas:
        resumen[f["estado_respaldo"]] = resumen.get(f["estado_respaldo"], 0) + 1
    inst = sorted({f["instancia"] for f in filas if f["instancia"]})
    return {"discos": len(filas), "por_estado": resumen, "instancias_afectadas": inst,
            "criterio": "PROTEGIDO: política y último backup vigente según su frecuencia; ATENCION: backups vencidos o solo manuales; SIN RESPALDO: ningún backup",
            **_limitar(filas)}


def estado_bases_datos(con, a: ArgsBD):
    where, params = _where([("ambiente = ?", a.ambiente),
                            ("auto_backup = ?", None if a.auto_backup is None else ("Sí" if a.auto_backup else "No"))])
    filas = _filas(con, f"""SELECT nombre, region, ambiente, rol, ocpus, almacenamiento_gb, modelo_licencia, version_bd,
                            auto_backup, ultimo_backup_bd FROM bases_datos{where} ORDER BY nombre""", params)
    if a.version_menor_a:
        lim = tuple(int(x) for x in a.version_menor_a.split("."))
        filas = [f for f in filas if tuple(int(x) for x in f["version_bd"].split(".")[:2]) < lim]
    return {"total": len(filas), **_limitar(filas)}


def recursos_huerfanos(con, a: ArgsHuerfanos):
    mes = a.mes or periodo(con)["hasta"][:7]
    ok, p = _mes_valido(con, mes)
    if a.tipo == "volumenes":
        filas = _filas(con, """SELECT nombre, 'BOOT' AS tipo, region, tamano_gb, substr(creado,1,10) AS creado, volume_id
                               FROM boot_volumes WHERE instance_id IS NULL
                               UNION ALL SELECT nombre, 'BLOCK', region, tamano_gb, substr(creado,1,10), volume_id
                               FROM block_volumes WHERE instance_id IS NULL ORDER BY tamano_gb DESC""")
        costos = dict(con.execute("""SELECT recurso_id, sum(costo_usd) FROM costos_diarios WHERE fecha LIKE ?
                                     AND sku != 'Block Volume - Backup Storage' GROUP BY recurso_id""", (mes + "%",)).fetchall())
        for f in filas:
            f["costo_mes_usd"] = _r(costos.get(f.pop("volume_id"), 0.0)) if ok else None
        return {"tipo": "volúmenes sin instancia asociada", "cantidad": len(filas),
                "gb_totales": sum(f["tamano_gb"] for f in filas), "mes_costo": mes if ok else None,
                "costo_total_mes_usd": _r(sum(f["costo_mes_usd"] or 0 for f in filas)) if ok else None,
                "nota": "costo de almacenamiento y rendimiento, sin incluir backups", **_limitar(filas)}
    filas = _filas(con, """SELECT backup_id, region, tipo_volumen, tamano_unico_gb, substr(creado,1,10) AS creado
                           FROM backups_volumen WHERE volume_id NOT IN
                           (SELECT volume_id FROM boot_volumes UNION SELECT volume_id FROM block_volumes)
                           ORDER BY tamano_unico_gb DESC""")
    ids = [f["backup_id"] for f in filas]
    costo = con.execute(f"""SELECT sum(costo_usd) FROM costos_diarios WHERE fecha LIKE ? AND recurso_id IN
                            ({','.join('?' * len(ids))})""", (mes + "%", *ids)).fetchone()[0] if ids and ok else None
    for f in filas:
        f["backup_id"] = "…" + f["backup_id"][-8:]
    return {"tipo": "backups sin volumen de origen", "cantidad": len(filas),
            "gb_unicos_totales": round(sum(f["tamano_unico_gb"] for f in filas), 1),
            "mes_costo": mes if ok else None, "costo_total_mes_usd": _r(costo), **_limitar(filas)}


def consultar_costos(con, a: ArgsCostos):
    ok, p = _mes_valido(con, a.mes)
    if not ok:
        return {"sin_datos": True, "mes_solicitado": a.mes, "periodo_disponible": p}
    conds = [("fecha LIKE ?", a.mes + "%"), ("region = ?", a.region), ("servicio = ?", a.servicio),
             ("sku LIKE ?", f"%{a.sku_contiene}%" if a.sku_contiene else None)]
    where, params = _where(conds)
    if a.recursos:
        where += f" AND recurso_nombre IN ({','.join('?' * len(a.recursos))})"
        params += a.recursos
    total = con.execute(f"SELECT sum(costo_usd) FROM costos_diarios{where}", params).fetchone()[0] or 0.0
    res = {"mes": a.mes, "filtros": {k: v for k, v in a.model_dump().items() if v not in (None, "total") and k not in ("mes", "top", "agrupar_por")},
           "costo_total_usd": _r(total), "moneda": "USD", "periodo_disponible": p}
    col = {"region": "region", "servicio": "servicio", "recurso": "recurso_nombre", "dia": "fecha"}.get(a.agrupar_por)
    if col:
        filas = _filas(con, f"""SELECT {col} AS {a.agrupar_por}, round(sum(costo_usd),2) AS costo_usd
                               FROM costos_diarios{where} GROUP BY {col} ORDER BY sum(costo_usd) DESC""", params)
        res["agrupado_por"] = a.agrupar_por
        res["desglose"] = filas[:a.top]
        res["grupos_totales"] = len(filas)
    return res


def variacion_costos(con, a: ArgsVariacion):
    p = periodo(con)
    if a.tipo == "meses":
        if not (a.mes_a and a.mes_b):
            raise ValueError("tipo=meses requiere mes_a y mes_b")
        for m in (a.mes_a, a.mes_b):
            if not _mes_valido(con, m)[0]:
                return {"sin_datos": True, "mes_solicitado": m, "periodo_disponible": p}
        ta = round(con.execute("SELECT sum(costo_usd) FROM costos_diarios WHERE fecha LIKE ?", (a.mes_a + "%",)).fetchone()[0], 2)
        tb = round(con.execute("SELECT sum(costo_usd) FROM costos_diarios WHERE fecha LIKE ?", (a.mes_b + "%",)).fetchone()[0], 2)
        return {"mes_a": a.mes_a, "costo_mes_a_usd": ta, "mes_b": a.mes_b, "costo_mes_b_usd": tb,
                "diferencia_usd": round(tb - ta, 2), "variacion_pct": round(100 * (tb - ta) / ta, 2)}
    import datetime as dt
    fin = dt.date.fromisoformat(p["hasta"])
    ini_rec = (fin - dt.timedelta(days=a.dias - 1)).isoformat()
    ini_ant = (fin - dt.timedelta(days=2 * a.dias - 1)).isoformat()
    filas = _filas(con, """SELECT recurso_nombre AS recurso,
                             round(sum(CASE WHEN fecha >= ? THEN costo_usd ELSE 0 END),2) AS costo_ventana_reciente,
                             round(sum(CASE WHEN fecha < ? THEN costo_usd ELSE 0 END),2) AS costo_ventana_anterior,
                             round(sum(CASE WHEN fecha >= ? THEN costo_usd ELSE -costo_usd END),2) AS aumento_usd
                           FROM costos_diarios WHERE fecha >= ? GROUP BY recurso_nombre
                           ORDER BY aumento_usd DESC LIMIT ?""", (ini_rec, ini_rec, ini_rec, ini_ant, a.top))
    return {"ventana_reciente": f"{ini_rec} a {fin}", "ventana_anterior": f"{ini_ant} a {dt.date.fromisoformat(ini_rec) - dt.timedelta(days=1)}",
            "mayores_aumentos": filas}


def instancias_detenidas_con_costo(con, a: ArgsMes):
    ok, p = _mes_valido(con, a.mes)
    if not ok:
        return {"sin_datos": True, "mes_solicitado": a.mes, "periodo_disponible": p}
    filas = _filas(con, """SELECT i.nombre, i.shape, i.region, round(sum(c.costo_usd),2) AS costo_mes_usd
                           FROM instancias i JOIN costos_diarios c ON c.recurso_id = i.instance_id
                           WHERE i.estado='STOPPED' AND c.fecha LIKE ? AND c.servicio='Compute'
                           GROUP BY i.nombre ORDER BY costo_mes_usd DESC""", (a.mes + "%",))
    return {"mes": a.mes, "cantidad": len(filas),
            "nota": "En OCI, los shapes bare metal, GPU y Dense I/O se facturan aunque estén detenidos", **_limitar(filas)}


def reglas_ingreso(con, a: ArgsReglas):
    conds = [("security_list = ?", a.security_list), ("origen = ?", "0.0.0.0/0" if a.solo_publicas else None)]
    where, params = _where(conds)
    if a.puerto is not None:
        where += (" AND " if where else " WHERE ") + "puerto_min <= ? AND puerto_max >= ?"
        params += [a.puerto, a.puerto]
    if a.excluir_web_balanceador:
        where += (" AND " if where else " WHERE ") + "NOT (security_list LIKE '%-lb' AND puerto_min IN (80, 443))"
    filas = _filas(con, f"""SELECT regla_id, region, vcn, security_list, protocolo, puerto_min, puerto_max, origen,
                            descripcion FROM reglas_ingreso{where} ORDER BY security_list, regla_id""", params)
    for f in filas:
        f["descripcion"] = _no_confiable(f["descripcion"])
    return {"total_reglas": len(filas), "security_lists": sorted({f["security_list"] for f in filas}), **_limitar(filas)}


def buckets(con, a: ArgsBuckets):
    conds = [("tier = ?", a.tier), ("tamano_gb > ?", a.min_gb),
             ("politica_ciclo_vida = ?", None if a.sin_ciclo_vida is None else ("No" if a.sin_ciclo_vida else "Sí"))]
    where, params = _where(conds)
    if a.publicos is not None:
        where += (" AND " if where else " WHERE ") + ("acceso_publico != 'NoPublicAccess'" if a.publicos else "acceso_publico = 'NoPublicAccess'")
    filas = _filas(con, f"""SELECT nombre, region, tier, tamano_gb, objetos, acceso_publico, versionado,
                            politica_ciclo_vida, freeform_tags FROM buckets{where} ORDER BY tamano_gb DESC""", params)
    for f in filas:
        tags = json.loads(f.pop("freeform_tags") or "{}")
        f["tags"] = {k: _no_confiable(v) for k, v in tags.items()}
    return {"total": len(filas), "gb_totales": round(sum(f["tamano_gb"] for f in filas), 1), **_limitar(filas)}


def detalle_recurso(con, a: ArgsDetalle):
    r = con.execute("SELECT * FROM instancias WHERE nombre = ?", (a.nombre,)).fetchone()
    if r:
        d = dict(r)
        d.pop("instance_id"); d.pop("compartment")
        ff = json.loads(d.pop("freeform_tags") or "{}")
        d["freeform_tags"] = {k: _no_confiable(v) for k, v in ff.items()}
        d["defined_tags"] = json.loads(d["defined_tags"])
        return {"tipo": "instancia", "recurso": d}
    for tabla, tipo in (("bases_datos", "base de datos"), ("buckets", "bucket"),
                        ("boot_volumes", "boot volume"), ("block_volumes", "block volume")):
        r = con.execute(f"SELECT * FROM {tabla} WHERE nombre = ?", (a.nombre,)).fetchone()
        if r:
            d = {k: v for k, v in dict(r).items() if not k.endswith("_id")}
            if "freeform_tags" in d:
                d["freeform_tags"] = {k: _no_confiable(v) for k, v in json.loads(d["freeform_tags"] or "{}").items()}
            return {"tipo": tipo, "recurso": d}
    return {"encontrado": False, "nombre": a.nombre}


# ─────────────────────────────── registro de tools
TOOLS: dict[str, tuple[Callable, type[BaseModel], str]] = {
    "consultar_instancias": (consultar_instancias, ArgsInstancias,
                             "Cuenta y lista instancias de cómputo con filtros opcionales. Devuelve totales (instancias, OCPUs, memoria) ya calculados."),
    "cumplimiento_etiquetado": (cumplimiento_etiquetado, ArgsVacios,
                                "Porcentaje de instancias con los 4 tags obligatorios completos y la lista de incompletas."),
    "cobertura_respaldo": (cobertura_respaldo, ArgsCobertura,
                           "Estado de respaldo de cada disco (boot y block): PROTEGIDO, ATENCION o SIN RESPALDO, con las instancias afectadas."),
    "estado_bases_datos": (estado_bases_datos, ArgsBD,
                           "DB Systems con su versión, licencia y si el respaldo automático está habilitado."),
    "recursos_huerfanos": (recursos_huerfanos, ArgsHuerfanos,
                           "Volúmenes sin instancia o backups sin volumen de origen, con tamaño y costo del mes."),
    "consultar_costos": (consultar_costos, ArgsCostos,
                         "Costo de un mes (total o agrupado por región, servicio, recurso o día), con filtros. Si el mes está fuera del periodo, devuelve sin_datos."),
    "variacion_costos": (variacion_costos, ArgsVariacion,
                         "Variación del costo total entre dos meses (tipo=meses) o recursos con mayor aumento en los últimos N días frente a los N anteriores (tipo=recursos)."),
    "instancias_detenidas_con_costo": (instancias_detenidas_con_costo, ArgsMes,
                                       "Instancias en estado STOPPED que igual generaron costo de cómputo en el mes."),
    "reglas_ingreso": (reglas_ingreso, ArgsReglas,
                       "Reglas de ingreso de las security lists, con filtros por lista, puerto u origen 0.0.0.0/0."),
    "buckets": (buckets, ArgsBuckets,
                "Buckets de Object Storage con tier, tamaño, acceso público y política de ciclo de vida."),
    "detalle_recurso": (detalle_recurso, ArgsDetalle,
                        "Detalle completo de un recurso por su nombre exacto, incluidos sus tags."),
}


def _aplanar(schema: dict) -> dict:
    """Esquema JSON simple para el LLM: sin 'title' y con Optional[X] convertido en X."""
    props = {}
    for nombre, p in schema.get("properties", {}).items():
        p = dict(p)
        if "anyOf" in p:
            tipos = [t for t in p.pop("anyOf") if t.get("type") != "null"]
            p.update(tipos[0] if tipos else {})
        p.pop("title", None)
        p.pop("default", None) if p.get("default") is None else None
        props[nombre] = p
    out = {"type": "object", "properties": props}
    if schema.get("required"):
        out["required"] = schema["required"]
    return out


def especificaciones() -> list[dict]:
    """Definición de tools en formato OpenAI/Ollama."""
    return [{"type": "function", "function": {"name": n, "description": d, "parameters": _aplanar(m.model_json_schema())}}
            for n, (_, m, d) in TOOLS.items()]


def ejecutar(con, nombre: str, argumentos: dict | str | None) -> dict:
    """Valida y ejecuta una tool. Lanza KeyError (tool inexistente) o ValidationError (argumentos inválidos)."""
    fn, modelo, _ = TOOLS[nombre]
    if isinstance(argumentos, str):
        argumentos = json.loads(argumentos or "{}")
    args = modelo.model_validate({k: v for k, v in (argumentos or {}).items() if v is not None})
    return fn(con, args)
