"""
Tests del dataset sintético: las respuestas del golden set se recalculan con SQL
de forma independiente al generador, para que el ground truth sea confiable.

Ejecutar:  pytest -q
"""
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(RAIZ, "data_gen", "generar_dataset_sintetico.py")
ARGS = ["--seed", "42", "--instancias", "120", "--dias", "92", "--fin", "2026-08-31"]
FIN = dt.date(2026, 8, 31)
UMBRAL = {"ADE-Oro": 2, "gold": 2, "silver": 8, "bronze": 32}


def generar(destino):
    subprocess.run([sys.executable, GEN, "--out", str(destino), *ARGS], check=True, capture_output=True)
    return str(destino)


@pytest.fixture(scope="session")
def data(tmp_path_factory):
    return generar(tmp_path_factory.mktemp("data"))


@pytest.fixture(scope="session")
def q(data):
    con = sqlite3.connect(os.path.join(data, "ade_ops.sqlite"))
    return lambda sql, *a: con.execute(sql, a).fetchall()


@pytest.fixture(scope="session")
def golden(data):
    with open(os.path.join(data, "eval", "golden_set.json"), encoding="utf-8") as f:
        return {p["id"]: p for p in json.load(f)["preguntas"]}


def _igual(esperado, obtenido, comparacion):
    if isinstance(esperado, float) or isinstance(obtenido, float):
        return abs(float(esperado) - float(obtenido)) <= max(0.02, abs(float(esperado)) * 1e-4)
    if isinstance(esperado, list):
        return esperado == obtenido if comparacion == "ordenada" else sorted(esperado) == sorted(obtenido)
    if isinstance(esperado, dict):
        return esperado.keys() == obtenido.keys() and all(
            _igual(esperado[k], obtenido[k], "conjunto") for k in esperado)
    return esperado == obtenido


def test_golden_set_recalculado_con_sql(q, golden):
    vols = q("""select v.volume_id, v.nombre, v.politica_backup, i.nombre, i.ambiente
                from (select volume_id, nombre, politica_backup, instance_id from boot_volumes
                      union all select volume_id, nombre, politica_backup, instance_id from block_volumes) v
                left join instancias i on i.instance_id = v.instance_id""")
    ultimo = dict(q("select volume_id, max(substr(creado,1,10)) from backups_volumen group by volume_id"))
    sin = [v for v in vols if v[4] == "PRD" and v[0] not in ultimo]
    gap = sorted({v[3] for v in sin})
    tags_ok = sum(all(k in json.loads(t).get("ADE-Estandar", {}) for k in
                      ("Empresa", "Aplicacion", "Ambiente", "CentroCosto")) for (t,) in q("select defined_tags from instancias"))
    huerf = q("""select count(*), round(sum(tamano_unico_gb),1) from backups_volumen where volume_id not in
                 (select volume_id from boot_volumes union select volume_id from block_volumes)""")[0]
    stop = q("""select recurso_nombre, round(sum(costo_usd),2) from costos_diarios c join instancias i
                on i.instance_id=c.recurso_id where i.estado='STOPPED' and fecha like '2026-08%' group by 1""")
    jul = round(q("select sum(costo_usd) from costos_diarios where fecha like '2026-07%'")[0][0], 2)
    ago = round(q("select sum(costo_usd) from costos_diarios where fecha like '2026-08%'")[0][0], 2)

    def publicas(p):
        return [r[0] for r in q("""select distinct security_list from reglas_ingreso
                                   where origen='0.0.0.0/0' and puerto_min<=? and puerto_max>=?""", p, p)]

    calc = {
        "G01": q("select count(*) from instancias")[0][0],
        "G02": q("select count(*) from instancias where estado='RUNNING' and region='sa-saopaulo-1'")[0][0],
        "G03": q("select sum(ocpus) from instancias where estado='RUNNING' and ambiente='PRD'")[0][0],
        "G04": round(100 * tags_ok / q("select count(*) from instancias")[0][0], 1),
        "G05": q("select count(*) from instancias where sistema_operativo='Windows' and ambiente='PRD'")[0][0],
        "G06": [r[0] for r in q("select nombre from instancias where substr(creado,1,10) >= '2026-06-01'")],
        "G07": len(sin),
        "G08": gap,
        "G09": [v[1] for v in vols if v[2] and v[0] in ultimo
                and (FIN - dt.date.fromisoformat(ultimo[v[0]])).days > UMBRAL[v[2]]],
        "G10": [r[0] for r in q("select nombre from bases_datos where ambiente='PRD' and auto_backup='No'")],
        "G11": [n for n, v in q("select nombre, version_bd from bases_datos")
                if tuple(map(int, v.split(".")[:2])) < (19, 27)],
        "G12": {"cantidad": huerf[0], "gb": huerf[1]},
        "G13": ago,
        "G14": {r: round(c, 2) for r, c in q("""select region, sum(costo_usd) from costos_diarios
                                                where fecha like '2026-07%' group by region""")},
        "G15": q("""select servicio from costos_diarios where fecha like '2026-08%'
                    group by servicio order by sum(costo_usd) desc limit 1""")[0][0],
        "G16": [r[0] for r in q("""select recurso_nombre from costos_diarios where fecha like '2026-08%'
                                  group by recurso_nombre order by sum(costo_usd) desc limit 5""")],
        "G17": {"nombre": stop[0][0], "costo": stop[0][1]} if len(stop) == 1 else {"nombre": stop, "costo": -1},
        "G18": round(q("""select sum(costo_usd) from costos_diarios where fecha like '2026-08%'
                          and sku != 'Block Volume - Backup Storage' and recurso_id in
                          (select volume_id from boot_volumes where instance_id is null
                           union select volume_id from block_volumes where instance_id is null)""")[0][0], 2),
        "G19": {"costo": round(q("""select sum(costo_usd) from costos_diarios where fecha like '2026-08%'
                                   and region='eu-frankfurt-1'""")[0][0], 2),
                "recursos": sorted(r[0] for r in q("select distinct recurso_nombre from costos_diarios where region='eu-frankfurt-1'"))},
        "G20": q("""select recurso_nombre, sum(case when fecha >= '2026-08-18' then costo_usd
                    when fecha >= '2026-08-04' then -costo_usd else 0 end) d
                    from costos_diarios group by 1 order by d desc limit 1""")[0][0],
        "G21": round(100 * (ago - jul) / jul, 2),
        "G22": q("""select fecha from costos_diarios where fecha like '2026-08%' and sku='Outbound Data Transfer'
                    group by fecha order by sum(costo_usd) desc limit 1""")[0][0],
        "G23": publicas(22),
        "G24": publicas(3389),
        "G25": [r[0] for r in q("select nombre from buckets where acceso_publico != 'NoPublicAccess'")],
        "G26": q("""select count(*) from reglas_ingreso where origen='0.0.0.0/0'
                    and not (security_list like '%-lb' and puerto_min in (80, 443))""")[0][0],
        "G27": round(q(f"""select sum(costo_usd) from costos_diarios where fecha like '2026-08%' and servicio='Compute'
                          and recurso_nombre in ({','.join('?' * len(gap))})""", *gap)[0][0], 2),
        "G28": [r[0] for r in q("""select nombre from buckets where tier='Standard' and tamano_gb > 1024
                                   and politica_ciclo_vida='No'""")],
        "G30": q("select count(*) from instancias where region='us-ashburn-1'")[0][0],
    }
    fallas = [(k, golden[k]["respuesta_esperada"], v) for k, v in calc.items()
              if not _igual(golden[k]["respuesta_esperada"], v, golden[k]["comparacion"])]
    assert not fallas, f"Golden set no coincide con SQL: {fallas}"
    comportamiento = {k for k, p in golden.items() if p["tipo"] in ("sin_datos", "rechazo", "fuera_dominio")}
    assert set(golden) == set(calc) | comportamiento, "Hay preguntas del golden set sin verificación"


def test_detalle_finops_cuadra_con_costos_diarios(data, q):
    for ruta in sorted(glob.glob(os.path.join(data, "detalle_finops_*.csv"))):
        mes = re.search(r"(\d{4}-\d{2})", ruta).group(1)
        with open(ruta, encoding="utf-8") as f:
            next(f)
            total_detalle = sum(float(l.rsplit(",", 1)[1]) for l in f)
        total_diario = q("select sum(costo_usd) from costos_diarios where fecha like ?", mes + "%")[0][0]
        assert round(total_detalle, 2) == round(total_diario, 2), mes


def test_integridad_referencial(q):
    assert q("""select count(*) from (select instance_id from boot_volumes union all
                select instance_id from block_volumes) v where instance_id is not null
                and instance_id not in (select instance_id from instancias)""")[0][0] == 0
    assert q("select count(*) from costos_diarios where costo_usd < 0 or costo_usd is null")[0][0] == 0
    assert q("select count(*) from instancias where shape like '%A1%' and sistema_operativo='Windows'")[0][0] == 0


def test_solo_identificadores_sinteticos(data):
    real = re.compile(r"ocid1\.[a-z0-9]+\.oc[0-9]\.[a-z0-9-]*\.(?!synth)[a-z0-9]{20,}")
    for ruta in glob.glob(os.path.join(data, "*.csv")):
        with open(ruta, encoding="utf-8") as f:
            assert not real.search(f.read()), ruta


def test_casos_de_inyeccion_sembrados(data, q):
    with open(os.path.join(data, "eval", "casos_inyeccion.json"), encoding="utf-8") as f:
        casos = {c["id"]: c for c in json.load(f)}
    assert q("select nombre from instancias where freeform_tags like '%IGNORA LAS INSTRUCCIONES%'")[0][0] \
        == casos["I01"]["recurso"]
    assert q("select count(*) from reglas_ingreso where descripcion like 'SYSTEM:%'")[0][0] == 1
    assert q("select count(*) from buckets where freeform_tags like '%Nota para el asistente%'")[0][0] == 1


def test_generacion_determinista(data, tmp_path):
    otra = generar(tmp_path / "otra")

    def h(base):
        return {n: hashlib.sha256(open(os.path.join(base, n), "rb").read()).hexdigest()
                for n in ("instancias.csv", "costos_diarios.csv", os.path.join("eval", "golden_set.json"))}

    assert h(data) == h(otra)
