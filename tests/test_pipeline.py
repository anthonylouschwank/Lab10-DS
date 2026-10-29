"""Pruebas del pipeline con datos sinteticos: publicacion, reproducibilidad y los seis controles."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from pipeline import calidad
from pipeline import procedimiento as proc
from pipeline.configuracion import cargar
from pipeline.run import ejecutar

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def base_sintetica() -> pd.DataFrame:
    """Misma estructura que la base de migracion, 2022-01 a 2026-06, con estacionalidad y crecimiento."""
    filas = []
    for i, p in enumerate(pd.period_range("2022-01", "2026-06", freq="M")):
        nivel = 1000 * (1.02 ** (i / 12)) * (1 + 0.2 * np.sin(2 * np.pi * p.month / 12))
        for tipo, escala in (("Turista", 1.0), ("Excursionista", 0.3), ("Viajero", 0.5)):
            for frontera in ("01 La Aurora", "14 Tecún Umán"):
                filas.append({
                    "Año": p.year, "Mes cod": p.month, "Mes": MESES[p.month - 1], "Vía": "Aérea",
                    "Frontera": frontera, "País": "México", "Agrupación Residencia": "México",
                    "Tipo de Viajero": tipo, "Viajero": round(nivel * escala, 2),
                })
    return pd.DataFrame(filas)


@pytest.fixture
def entorno(tmp_path):
    def preparar(raw: pd.DataFrame, formato: str = "parquet") -> dict:
        fuente = tmp_path / f"base.{formato}"
        raw.to_csv(fuente, index=False) if formato == "csv" else raw.to_parquet(fuente, index=False)
        return cargar(fuente=str(fuente), salidas=str(tmp_path / "salidas"))
    return preparar


def estados(manifiesto: dict) -> dict:
    return manifiesto.get("calidad", {})


def test_ejecucion_publica_y_es_reproducible(entorno):
    cfg = entorno(base_sintetica())
    a, b = ejecutar(cfg), ejecutar(cfg)
    assert a["estado"] == b["estado"] == "publicada"
    ea = pd.read_parquet(f"{a['carpeta']}/estimaciones.parquet")
    eb = pd.read_parquet(f"{b['carpeta']}/estimaciones.parquet")
    pd.testing.assert_series_equal(ea["valor"], eb["valor"])
    assert list(ea["periodo"]) == [str(p) for p in proc.rango(cfg["periodos"]["estimacion"])]
    assert {"destino", "periodo", "valor", "unidad", "id_ejecucion", "fecha_generacion", "version_procedimiento"} <= set(ea.columns)
    vigente = json.loads((cfg["rutas"]["salidas"] / "vigente.json").read_text(encoding="utf-8"))
    assert vigente["id_ejecucion"] == b["id_ejecucion"] and vigente["anterior"] == a["id_ejecucion"]


def test_evaluacion_no_usa_informacion_futura(entorno):
    cfg = entorno(base_sintetica())
    y = proc.construir_serie(calidad.validar(pd.read_parquet(cfg["rutas"]["fuente"]), cfg)[1], cfg)["destino"]
    origen = proc.origenes(cfg)["evaluacion"]
    meses = proc.rango(cfg["periodos"]["evaluacion"])
    alterada = y.copy()
    alterada[alterada.index > origen] *= 10
    pd.testing.assert_series_equal(proc.estimar(y, origen, meses, 12)[0], proc.estimar(alterada, origen, meses, 12)[0])


def _falla_y_conserva_vigente(entorno, raw_bueno, raw_malo, control, formato="parquet"):
    cfg = entorno(raw_bueno)
    aprobada = ejecutar(cfg)
    cfg_malo = entorno(raw_malo, formato)
    fallida = ejecutar(cfg_malo)
    assert fallida["estado"] == "fallida"
    assert estados(fallida)[control] == calidad.CRITICO
    assert "estimacion" not in fallida["etapas_completadas"]
    vigente = json.loads((cfg["rutas"]["salidas"] / "vigente.json").read_text(encoding="utf-8"))
    assert vigente["id_ejecucion"] == aprobada["id_ejecucion"]


def test_a_columna_indispensable_ausente(entorno):
    raw = base_sintetica()
    _falla_y_conserva_vigente(entorno, raw, raw.drop(columns="Viajero"), "a_columnas_tipos")


def test_a_tipo_incompatible(entorno):
    raw = base_sintetica()
    malo = raw.astype({"Viajero": "object"})
    malo.loc[5, "Viajero"] = "sin dato"
    _falla_y_conserva_vigente(entorno, raw, malo, "a_columnas_tipos", formato="csv")


def test_b_mes_sin_cobertura_no_se_rellena_con_cero(entorno):
    raw = base_sintetica()
    malo = raw[~((raw["Año"] == 2024) & (raw["Mes cod"] == 3))]
    _falla_y_conserva_vigente(entorno, raw, malo, "b_fechas_cobertura")
    cfg = entorno(malo)
    df = calidad.validar(malo, cfg)[1]
    assert np.isnan(proc.construir_serie(df, cfg).loc[pd.Period("2024-03", "M"), "destino"])


def test_b_fecha_invalida(entorno):
    raw = base_sintetica()
    malo = raw.copy()
    malo.loc[0, "Mes cod"] = 13
    _falla_y_conserva_vigente(entorno, raw, malo, "b_fechas_cobertura")


def test_c_clave_duplicada(entorno):
    raw = base_sintetica()
    malo = pd.concat([raw, raw[raw["Tipo de Viajero"] == "Turista"].head(1)])
    _falla_y_conserva_vigente(entorno, raw, malo, "c_unicidad")


def test_c_duplicado_en_tipo_no_usado_solo_advierte(entorno):
    raw = pd.concat([base_sintetica(), base_sintetica().query("`Tipo de Viajero` == 'Viajero'").head(1)])
    assert ejecutar(entorno(raw))["calidad"]["c_unicidad"] == calidad.ADVERTENCIA


def test_d_faltante_que_impide_estimar(entorno):
    raw = base_sintetica()
    malo = raw.copy()
    malo.loc[malo["Tipo de Viajero"] == "Turista", "Viajero"] = malo["Viajero"].where(malo.index != 0)
    _falla_y_conserva_vigente(entorno, raw, malo, "d_faltantes")


def test_d_faltante_permitido(entorno):
    raw = base_sintetica()
    raw.loc[raw["Tipo de Viajero"] == "Viajero", "Viajero"] = np.nan
    raw["Frontera"] = raw["Frontera"].where(raw.index != 3)
    assert ejecutar(entorno(raw))["calidad"]["d_faltantes"] == calidad.ADVERTENCIA


def test_e_conteo_negativo(entorno):
    raw = base_sintetica()
    malo = raw.copy()
    malo.loc[0, "Viajero"] = -5
    _falla_y_conserva_vigente(entorno, raw, malo, "e_valores_denominadores")


def test_e_denominador_cero(entorno):
    raw = base_sintetica()
    malo = raw.copy()
    # Ventana del denominador de r para el origen de evaluacion (2025-06): 2023-07 a 2024-06
    meses = malo["Año"] * 12 + malo["Mes cod"]
    malo.loc[meses.between(2023 * 12 + 7, 2024 * 12 + 6), "Viajero"] = 0
    _falla_y_conserva_vigente(entorno, raw, malo, "e_valores_denominadores")


def test_f_columna_diaria(entorno):
    raw = base_sintetica()
    _falla_y_conserva_vigente(entorno, raw, raw.assign(Día=1), "f_regla_metodologica")


def test_f_tipo_que_no_es_visitante(entorno):
    cfg = entorno(base_sintetica())
    cfg["reparto"]["factores"]["Viajero"] = 0.1
    resultados, _ = calidad.validar(base_sintetica(), cfg)
    assert {r.control: r.estado for r in resultados}["f_regla_metodologica"] == calidad.CRITICO
