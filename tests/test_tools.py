"""
Criterio de aceptación de la RECUPERACIÓN: cada pregunta del golden set se puede
responder con UNA llamada a tools (o una cadena corta), y el resultado contiene
exactamente el valor esperado. Si esto falla, ningún LLM podrá acertar.
"""
import json
import os
import subprocess
import sys

import pytest
from pydantic import ValidationError

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from backend import tools  # noqa: E402


@pytest.fixture(scope="module")
def entorno(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    subprocess.run([sys.executable, os.path.join(RAIZ, "data_gen", "generar_dataset_sintetico.py"), "--out", str(d)],
                   check=True, capture_output=True)
    con = tools.conectar(d / "ade_ops.sqlite")
    g = {p["id"]: p["respuesta_esperada"] for p in json.load(open(d / "eval" / "golden_set.json", encoding="utf-8"))["preguntas"]}
    return con, g


def t(con, _tool, **args):
    return tools.ejecutar(con, _tool, args)


def test_golden_set_respondible_con_tools(entorno):
    con, g = entorno
    chequeos = {
        "G01": t(con, "consultar_instancias")["total_instancias"],
        "G02": t(con, "consultar_instancias", region="sa-saopaulo-1", estado="RUNNING")["total_instancias"],
        "G03": t(con, "consultar_instancias", ambiente="PRD", estado="RUNNING")["ocpus_total"],
        "G04": t(con, "cumplimiento_etiquetado")["porcentaje_cumplimiento"],
        "G05": t(con, "consultar_instancias", ambiente="PRD", sistema_operativo="Windows")["total_instancias"],
        "G06": [f["nombre"] for f in t(con, "consultar_instancias", creadas_desde="2026-06-01")["filas"]],
        "G07": t(con, "cobertura_respaldo", ambiente="PRD", estado_respaldo="SIN RESPALDO")["discos"],
        "G08": t(con, "cobertura_respaldo", ambiente="PRD", estado_respaldo="SIN RESPALDO")["instancias_afectadas"],
        "G09": [f["disco"] for f in t(con, "cobertura_respaldo", estado_respaldo="ATENCION", con_politica=True)["filas"]],
        "G10": [f["nombre"] for f in t(con, "estado_bases_datos", ambiente="PRD", auto_backup=False)["filas"]],
        "G11": [f["nombre"] for f in t(con, "estado_bases_datos", version_menor_a="19.27")["filas"]],
        "G12": (lambda r: {"cantidad": r["cantidad"], "gb": r["gb_unicos_totales"]})(t(con, "recursos_huerfanos", tipo="backups")),
        "G13": t(con, "consultar_costos", mes="2026-08")["costo_total_usd"],
        "G14": {d["region"]: d["costo_usd"] for d in t(con, "consultar_costos", mes="2026-07", agrupar_por="region")["desglose"]},
        "G15": t(con, "consultar_costos", mes="2026-08", agrupar_por="servicio")["desglose"][0]["servicio"],
        "G16": [d["recurso"] for d in t(con, "consultar_costos", mes="2026-08", agrupar_por="recurso", top=5)["desglose"]],
        "G17": (lambda f: {"nombre": f["nombre"], "costo": f["costo_mes_usd"]})(t(con, "instancias_detenidas_con_costo", mes="2026-08")["filas"][0]),
        "G18": t(con, "recursos_huerfanos", tipo="volumenes", mes="2026-08")["costo_total_mes_usd"],
        "G19": (lambda r: {"costo": r["costo_total_usd"], "recursos": sorted(d["recurso"] for d in r["desglose"])})(
            t(con, "consultar_costos", mes="2026-08", region="eu-frankfurt-1", agrupar_por="recurso")),
        "G20": t(con, "variacion_costos", tipo="recursos", dias=14)["mayores_aumentos"][0]["recurso"],
        "G21": t(con, "variacion_costos", tipo="meses", mes_a="2026-07", mes_b="2026-08")["variacion_pct"],
        "G22": t(con, "consultar_costos", mes="2026-08", sku_contiene="Outbound Data Transfer", agrupar_por="dia")["desglose"][0]["dia"],
        "G23": t(con, "reglas_ingreso", puerto=22, solo_publicas=True)["security_lists"],
        "G24": t(con, "reglas_ingreso", puerto=3389, solo_publicas=True)["security_lists"],
        "G25": [f["nombre"] for f in t(con, "buckets", publicos=True)["filas"]],
        "G26": t(con, "reglas_ingreso", solo_publicas=True, excluir_web_balanceador=True)["total_reglas"],
        "G28": [f["nombre"] for f in t(con, "buckets", tier="Standard", min_gb=1024, sin_ciclo_vida=True)["filas"]],
        "G30": t(con, "consultar_instancias", region="us-ashburn-1")["total_instancias"],
    }
    inst = t(con, "cobertura_respaldo", ambiente="PRD", estado_respaldo="SIN RESPALDO")["instancias_afectadas"]
    chequeos["G27"] = t(con, "consultar_costos", mes="2026-08", servicio="Compute", recursos=inst)["costo_total_usd"]
    fallas = []
    for k, v in chequeos.items():
        e = g[k]
        ok = (sorted(e) == sorted(v) if isinstance(e, list) and k != "G16" else
              abs(e - v) < 0.02 if isinstance(e, float) else
              all(abs(e[x] - v[x]) < 0.2 if isinstance(e[x], float) else e[x] == v[x] for x in e) if isinstance(e, dict) else e == v)
        if not ok:
            fallas.append((k, e, v))
    assert not fallas, fallas


def test_mes_fuera_de_periodo_devuelve_sin_datos(entorno):
    con, _ = entorno
    r = t(con, "consultar_costos", mes="2025-03")
    assert r["sin_datos"] and r["periodo_disponible"]["desde"] == "2026-06-01"


def test_argumentos_invalidos_se_rechazan(entorno):
    con, _ = entorno
    with pytest.raises(ValidationError):
        t(con, "consultar_costos", mes="agosto")
    with pytest.raises(ValidationError):
        t(con, "consultar_instancias", ambiente="PROD")
    with pytest.raises(ValidationError):
        t(con, "consultar_instancias", region="x'; DROP TABLE instancias;--")
    with pytest.raises(KeyError):
        t(con, "borrar_instancia", nombre="x")


def test_solo_lectura(entorno):
    con, _ = entorno
    import sqlite3
    with pytest.raises(sqlite3.OperationalError):
        con.execute("DELETE FROM instancias")


def test_texto_libre_marcado_como_no_confiable(entorno):
    con, _ = entorno
    r = t(con, "reglas_ingreso", security_list="sl-ade-gru-prd-mgmt")
    desc = [f["descripcion"] for f in r["filas"] if isinstance(f["descripcion"], dict)]
    assert any("SYSTEM:" in d["_no_confiable"] for d in desc)
    b = t(con, "buckets")
    assert any("_no_confiable" in json.dumps(f["tags"]) for f in b["filas"] if f["tags"])


def test_especificaciones_validas():
    specs = tools.especificaciones()
    assert len(specs) == len(tools.TOOLS)
    for s in specs:
        p = s["function"]["parameters"]
        assert p["type"] == "object"
        assert all("anyOf" not in v for v in p["properties"].values())
