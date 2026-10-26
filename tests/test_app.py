"""Pruebas de humo: cada pagina corre sin excepciones con sus valores por defecto y en casos limite."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent

PAGINAS = [
    "paginas/explorar.py",
    "paginas/temporadas.py",
    "paginas/mercados.py",
    "paginas/modelos.py",
    "paginas/comparar.py",
    "paginas/acerca.py",
]


def correr(pagina: str) -> AppTest:
    at = AppTest.from_file(str(ROOT / pagina), default_timeout=60)
    at.run()
    return at


@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina_sin_errores(pagina):
    at = correr(pagina)
    assert not at.exception, at.exception


def test_app_navegacion_e_inicio():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    assert not at.exception


@pytest.mark.parametrize("pagina", ["paginas/explorar.py", "paginas/temporadas.py", "paginas/mercados.py"])
def test_filtros_vacios_muestran_mensaje(pagina):
    at = correr(pagina)
    tipos = next(m for m in at.multiselect if m.label == "Tipo de viajero")
    tipos.set_value([]).run()
    assert not at.exception
    assert any("No hay viajeros" in w.value for w in at.warning)


@pytest.mark.parametrize("nivel", ["Año", "Trimestre", "Mes"])
def test_explorar_niveles(nivel):
    at = correr("paginas/explorar.py")
    at.button_group(key="expl_nivel").set_value(nivel).run()
    assert not at.exception


def test_pronosticos_todas_las_series():
    at = correr("paginas/modelos.py")
    for opcion in at.selectbox(key="pron_serie").options:
        at.selectbox(key="pron_serie").set_value(opcion).run()
        assert not at.exception, opcion
        if opcion == "Vía Marítima":
            assert any("no tiene turistas ni excursionistas" in w.value for w in at.warning)


@pytest.mark.parametrize("nivel", ["Trimestre", "Año"])
def test_pronosticos_niveles(nivel):
    at = correr("paginas/modelos.py")
    at.button_group(key="pron_nivel").set_value(nivel).run()
    assert not at.exception


def test_pronosticos_sin_modelos():
    at = correr("paginas/modelos.py")
    at.multiselect(key="pron_modelos_Total mensual").set_value([]).run()
    assert not at.exception
    assert any("al menos un modelo" in w.value for w in at.warning)


@pytest.mark.parametrize("metrica", ["MAPE", "MAE", "RMSE"])
def test_comparar_metricas(metrica):
    at = correr("paginas/comparar.py")
    at.button_group(key="comp_metrica").set_value(metrica).run()
    assert not at.exception


def test_mercados_dimensiones_y_base():
    at = correr("paginas/mercados.py")
    for dim in at.selectbox(key="merc_dim").options:
        at.selectbox(key="merc_dim").set_value(dim).run()
        assert not at.exception, dim
    at.selectbox(key="merc_base").set_value(2009).run()
    assert not at.exception
    at.button_group(key="merc_prof").set_value("Regiones").run()
    assert not at.exception


@pytest.mark.parametrize("pagina,clave", [("paginas/comparar.py", "comp_vis"), ("paginas/explorar.py", "explorar_vis"), ("paginas/modelos.py", "pron_vis")])
def test_ocultar_todas_las_graficas(pagina, clave):
    at = correr(pagina)
    at.button_group(key=clave).set_value([]).run()
    assert not at.exception
    assert any("ocultas" in i.value for i in at.info)
