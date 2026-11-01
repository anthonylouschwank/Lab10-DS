"""Pruebas del pipeline con datos sinteticos: publicacion, reproducibilidad y los seis controles."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from mlflow.tracking import MlflowClient

from pipeline import calidad, consultar, monitoreo, restaurar
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
        cfg = cargar(fuente=str(fuente), salidas=str(tmp_path / "salidas"))
        cfg["mlflow"]["experimento"] = f"pruebas-{tmp_path.name}"
        return cfg
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


# MLflow (ejercicio 4)

def test_mlflow_registra_ejecucion_publicada(entorno):
    cfg = entorno(base_sintetica())
    m = ejecutar(cfg)
    client = MlflowClient()
    run = client.get_run(m["mlflow"]["run_id"])
    assert run.info.status == "FINISHED" and run.info.run_name == m["id_ejecucion"]
    tags, params, metricas = run.data.tags, run.data.params, run.data.metrics
    assert tags["estado"] == "publicada" and tags["git_commit"] == str(m["codigo"]["commit"] or "desconocido")
    assert tags["fuente_sha256"] == m["fuente"]["sha256"] and tags["calidad.c_unicidad"] == calidad.OK
    assert params["periodo_ajuste_inicio"] == cfg["periodos"]["ajuste"][0] and params["factor_Turista"] == "0.2"
    assert metricas["mape"] == pytest.approx(m["metricas"]["procedimiento"]["MAPE"])
    artefactos = {a.path for a in client.list_artifacts(run.info.run_id)}
    assert {"estimaciones.parquet", "config.yaml", "parametros.json", "calidad.json", "manifiesto.json", "registro.log"} <= artefactos


def test_mlflow_fallida_sin_metricas_y_con_causa(entorno):
    m = ejecutar(entorno(base_sintetica().drop(columns="Viajero")))
    run = MlflowClient().get_run(m["mlflow"]["run_id"])
    assert run.info.status == "FAILED" and run.data.tags["estado"] == "fallida"
    assert "a_columnas_tipos" in run.data.tags["error"] and "Viajero" in run.data.tags["error"]
    # solo conteos de calidad y monitoreo; ninguna metrica de evaluacion
    assert not {c for c in run.data.metrics if not c.startswith(("calidad_", "monitoreo_"))}


def test_mlflow_no_disponible_detiene_sin_publicar(entorno, monkeypatch):
    cfg = entorno(base_sintetica())
    aprobada = ejecutar(cfg)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:9")
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    m = ejecutar(cfg)
    assert m["estado"] == "fallida" and m["etapas_completadas"] == []
    vigente = json.loads((cfg["rutas"]["salidas"] / "vigente.json").read_text(encoding="utf-8"))
    assert vigente["id_ejecucion"] == aprobada["id_ejecucion"]


def test_version_publicada_incluye_manifiesto(entorno):
    cfg = entorno(base_sintetica())
    m = ejecutar(cfg)
    copia = json.loads((cfg["rutas"]["salidas"] / "versiones" / m["id_ejecucion"] / "manifiesto.json").read_text(encoding="utf-8"))
    assert copia["estado"] == "publicada" and copia["mlflow"]["run_id"] == m["mlflow"]["run_id"]


def test_consulta_reproducibilidad(entorno, tmp_path):
    cfg = entorno(base_sintetica())
    ejecutar(cfg), ejecutar(cfg)
    ejecutar(entorno(base_sintetica().drop(columns="Viajero")))
    tabla, repro = consultar.escribir_evidencia(cfg, tmp_path / "evidencia")
    assert len(tabla) == 3 and (tabla["estado"] == "fallida").sum() == 1
    assert repro["equivalentes"] and repro["diferencia_maxima"] == 0
    assert "sin metricas" in (tmp_path / "evidencia" / "mlflow_consulta.md").read_text(encoding="utf-8")


# Monitoreo (ejercicio 7.2): las alertas no rechazan la version por si solas

def test_monitoreo_primera_ejecucion(entorno):
    m = ejecutar(entorno(base_sintetica()))
    mon = m["monitoreo"]
    assert mon["calidad"]["estado"] == monitoreo.SIN_REFERENCIA
    assert mon["actualizacion"]["estado"] == mon["resultados"]["estado"] == monitoreo.OK


def test_monitoreo_alerta_de_calidad_sin_bloquear(entorno):
    cfg = entorno(base_sintetica())
    ejecutar(cfg)
    raw = pd.concat([base_sintetica(), base_sintetica().query("`Tipo de Viajero` == 'Viajero'").head(3)])
    m = ejecutar(entorno(raw))
    assert m["monitoreo"]["calidad"]["estado"] == monitoreo.ALERTA and "claves repetidas" in m["monitoreo"]["calidad"]["detalle"]
    assert m["estado"] == "publicada"


def test_monitoreo_fuente_atrasada(entorno):
    cfg = entorno(base_sintetica())
    cfg["monitoreo"]["ultimo_periodo_esperado"] = "2026-08"
    m = ejecutar(cfg)
    assert m["monitoreo"]["actualizacion"]["estado"] == monitoreo.ALERTA and "se esperaba 2026-08" in m["monitoreo"]["actualizacion"]["detalle"]


def test_monitoreo_cambio_frente_a_vigente(entorno):
    cfg = entorno(base_sintetica())
    ejecutar(cfg)
    cfg["reparto"]["factores"]["Turista"] = 0.3
    m = ejecutar(cfg)
    res = m["monitoreo"]["resultados"]
    assert res["estado"] == monitoreo.ALERTA and res["cambio_maximo_frente_a_vigente"] == pytest.approx(0.5)
    assert m["estado"] == "publicada"
    run = MlflowClient().get_run(m["mlflow"]["run_id"])
    assert run.data.tags["monitoreo.resultados"] == monitoreo.ALERTA and run.data.metrics["monitoreo_alertas"] == 1


# Restauracion (ejercicio 7.5)

def test_restaurar_version_anterior_y_volver(entorno):
    cfg = entorno(base_sintetica())
    salidas = cfg["rutas"]["salidas"]
    a, b = ejecutar(cfg), ejecutar(cfg)
    assert restaurar.main(["--salidas", str(salidas), "--anterior"]) == 0
    vig = restaurar.vigente(salidas)
    assert vig["id_ejecucion"] == a["id_ejecucion"] and vig["anterior"] == b["id_ejecucion"] and vig["restaurada"]
    assert restaurar.main(["--salidas", str(salidas), "--id", b["id_ejecucion"]]) == 0
    assert restaurar.vigente(salidas)["id_ejecucion"] == b["id_ejecucion"]
    assert restaurar.versiones(salidas) == sorted([a["id_ejecucion"], b["id_ejecucion"]])


def test_restaurar_version_inexistente_no_cambia_vigente(entorno):
    cfg = entorno(base_sintetica())
    m = ejecutar(cfg)
    assert restaurar.main(["--salidas", str(cfg["rutas"]["salidas"]), "--id", "no-existe"]) == 1
    assert restaurar.vigente(cfg["rutas"]["salidas"])["id_ejecucion"] == m["id_ejecucion"]
