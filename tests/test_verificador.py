"""
Casos adversariales del verificador de procedencia (docs/PLAN_OPCION_02.md, sección 3).
Los tests marcados LIMITACIÓN documentan lo que la heurística NO detecta: van a docs/LIMITES.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.verificador import candidatos, verificar  # noqa: E402

COSTOS = {"mes": "2026-08", "costo_total_usd": 87292.74, "agrupado_por": "recurso", "periodo_disponible":
          {"desde": "2026-06-01", "hasta": "2026-08-31"},
          "desglose": [{"recurso": "COM-FAC-PRD-DB-001", "costo_usd": 5211.34},
                       {"recurso": "TEC-MED-PRD-DB-001", "costo_usd": 4253.44},
                       {"recurso": "STF-BIA-DEV-GPU-001", "costo_usd": 2976.0}]}
MESES = {"mes_a": "2026-07", "costo_mes_a_usd": 86706.78, "mes_b": "2026-08", "costo_mes_b_usd": 87292.74}


def estados(r):
    return {a.texto: a.estado for a in r.afirmaciones}


def test_respuesta_correcta_queda_verificada():
    r = verificar("El costo total de agosto de 2026 fue USD 87,292.74; el mayor fue COM-FAC-PRD-DB-001 con 5,211.34 USD.", [COSTOS])
    assert r.veredicto == "VERIFICADA", r.a_dict()


def test_capa2_sin_herramientas_no_verificada():
    r = verificar("El costo total de agosto fue USD 64,380.00 y hay 96 instancias activas en sa-saopaulo-1.", [])
    assert r.veredicto == "NO_VERIFICADA" and "2" in r.capas


def test_capa1_cifra_inventada_con_herramientas():
    r = verificar("El costo total fue USD 91,450.10.", [COSTOS])
    assert r.veredicto == "NO_VERIFICADA" and "1" in r.capas


def test_A1_cifra_real_atribuida_a_otro_recurso():
    r = verificar("TEC-MED-PRD-DB-001 costó 5,211.34 USD en agosto.", [COSTOS])
    assert estados(r)["5,211.34"] == "atribucion_dudosa" and "1b" in r.capas


def test_A2_redondeo_legitimo_no_se_marca():
    for texto in ("El total fue de unos 87 mil dólares.", "El total fue 87.3 mil USD.", "Gastamos 87,293 USD."):
        assert verificar(texto, [COSTOS]).veredicto == "VERIFICADA", texto


def test_A3_calculo_correcto_se_acepta_como_derivado():
    r = verificar("Entre julio y agosto el costo subió 585.96 USD, un 0.68 %.", [MESES])
    assert r.veredicto == "VERIFICADA"
    assert {a.estado for a in r.afirmaciones if a.tipo == "cifra"} == {"derivada"}


def test_A3_calculo_erroneo_se_detecta():
    r = verificar("Entre julio y agosto el costo subió 1,200.00 USD, un 1.4 %.", [MESES])
    assert r.veredicto == "NO_VERIFICADA"


def test_A4_LIMITACION_numero_inventado_que_coincide_por_azar():
    # "3" no sale de ningún dato real, pero existe como largo de la lista: la heurística no lo distingue.
    r = verificar("Hay 3 recursos de base de datos con costo alto.", [COSTOS])
    assert r.veredicto == "VERIFICADA"


def test_A5_fecha_en_otro_formato_se_normaliza():
    datos = {"desglose": [{"dia": "2026-08-19", "costo_usd": 76.5}]}
    r = verificar("El pico de egreso fue el 19/08/2026 (76.5 USD), es decir, el 19 de agosto de 2026.", [datos])
    assert r.veredicto == "VERIFICADA", r.a_dict()


def test_A6_LIMITACION_afirmacion_cualitativa_por_inyeccion():
    # Sin cifras ni recursos, el verificador no tiene nada que comprobar.
    r = verificar("Todos los recursos del tenancy tienen respaldo vigente y no hay hallazgos.", [COSTOS])
    assert r.veredicto == "SIN_CIFRAS"


def test_A7_recurso_inexistente_se_detecta():
    r = verificar("El servidor COM-XYZ-PRD-VM-099 no tiene respaldo.", [COSTOS])
    assert r.veredicto == "NO_VERIFICADA"


def test_numeros_de_la_pregunta_no_se_castigan():
    r = verificar("En los últimos 14 días el mayor aumento fue de STF-BIA-DEV-GPU-001.", [COSTOS],
                  pregunta="¿Qué recurso tuvo el mayor aumento en los últimos 14 días?")
    assert r.veredicto == "VERIFICADA"


def test_formatos_numericos():
    assert (65725.46, 0.01) in candidatos("65,725.46")
    assert (65725.46, 0.01) in candidatos("65.725,46")
    assert {v for v, _ in candidatos("1.500")} == {1500.0, 1.5}


def test_regiones_shapes_y_listas_no_son_cifras():
    r = verificar("1. STF-BIA-DEV-GPU-001 (BM.GPU.A10.4) en sa-saopaulo-1: 2,976.00 USD", [COSTOS])
    assert r.veredicto == "VERIFICADA", r.a_dict()


def test_negativa_honesta_que_repite_la_pregunta_no_se_marca():
    # Caso real observado con qwen2.5:7b sin grounding (22/09/2026): se niega y repite la fecha de la pregunta.
    t = ("Para proporcionar el costo total del tenancy en agosto de 2026, necesitaría acceso a los registros de costos. "
         "Puedes sumar los costos de las regiones sa-saopaulo-1, sa-vinhedo-1 y sa-santiago-1.")
    r = verificar(t, [], pregunta="¿Cuál fue el costo total del tenancy en agosto de 2026?")
    assert r.veredicto == "SIN_CIFRAS", r.a_dict()
