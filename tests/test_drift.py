import pytest
from src.datos import dividir, generar
from src.drift import VARIABLES, alarma_rendimiento, revisar_datos


def test_mismo_origen_y_deriva_en_cada_variable():
    baseline, _, _ = dividir(generar())
    normal = generar(1000, 2026)
    assert revisar_datos(baseline, normal)["estado"] == "VERDE"
    for variable in VARIABLES:
        rojo = normal.copy()
        rojo[variable] = 60 if variable == "plazo_meses" else rojo[variable] * 4 + 20
        resultado = revisar_datos(baseline, rojo)
        assert next(r for r in resultado["variables"] if r["variable"] == variable)["alerta"]


def test_alarma_exige_persistencia_y_etiquetas():
    resultados = alarma_rendimiento([0.8, 0.65, 0.79, 0.65, 0.60, None], 0.8)
    assert [r["alarma"] for r in resultados] == [False, False, False, False, True, False]
    assert resultados[-1]["estado"] == "PENDIENTE_ETIQUETAS"


def test_rechaza_lote_sin_calidad():
    datos = generar(1000, 7)
    datos.loc[0, "ingreso_mensual"] = float("nan")
    with pytest.raises(ValueError, match="no finitos"):
        revisar_datos(generar(), datos)
