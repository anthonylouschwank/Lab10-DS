"""Monitoreo por ejecucion (Laboratorio 11, ejercicio 7.2).

Tres verificaciones, cada una "ok", "alerta" o "sin_referencia":
- actualizacion: la fuente cubre hasta el ultimo periodo esperado y las estimaciones empiezan el mes siguiente.
- calidad: cambios en filas, faltantes, claves repetidas y cobertura frente a la version aprobada vigente.
- resultados: estimaciones negativas o no finitas, variacion interanual y cambio frente a la version vigente.

Una alerta pide revision y queda en el registro, el manifiesto y MLflow; por si sola no rechaza la
version (eso lo decide la regla de aceptacion) ni demuestra perdida de precision.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import procedimiento as proc

OK, ALERTA, SIN_REFERENCIA = "ok", "alerta", "sin_referencia"


def perfil(df: pd.DataFrame, cfg: dict) -> dict:
    """Resumen de calidad de la fuente que se compara entre ejecuciones."""
    usados = df["tipo"].isin(proc.tipos_usados(cfg))
    validos = df[usados & df["viajeros"].notna() & df["anio"].notna() & df["mes"].notna()]
    periodos = proc.periodos_de(validos["anio"], validos["mes"])
    clave = [c for c in cfg["fuente"]["clave"] if c in df]
    return {
        "filas": int(len(df)),
        "faltantes_conteo_usados": int((df["viajeros"].isna() & usados).sum()),
        "faltantes_totales": int(df.isna().sum().sum()),
        "claves_repetidas": int(df.duplicated(clave, keep=False).sum()),
        "meses_con_datos": int(periodos.nunique()),
        "ultimo_periodo": str(periodos.max()) if len(periodos) else None,
    }


def leer_vigente(salidas: Path) -> tuple[dict | None, Path | None]:
    vigente = salidas / "vigente.json"
    if not vigente.exists():
        return None, None
    info = json.loads(vigente.read_text(encoding="utf-8"))
    return info, salidas / info["ruta"]


def actualizacion(actual: dict, cfg: dict, estimaciones: pd.DataFrame | None = None) -> dict:
    esperado = proc.periodo(cfg["monitoreo"]["ultimo_periodo_esperado"])
    ultimo = proc.periodo(actual["ultimo_periodo"]) if actual["ultimo_periodo"] else None
    avisos = []
    if ultimo is None or ultimo < esperado:
        avisos.append(f"la fuente llega a {ultimo}, se esperaba {esperado}")
    elif ultimo > esperado:
        avisos.append(f"la fuente ya cubre {ultimo}: actualizar periodos y cobertura esperada (hoy {esperado})")
    if estimaciones is not None and len(estimaciones):
        primero = proc.periodo(estimaciones["periodo"].iloc[0])
        if primero != esperado + 1:
            avisos.append(f"las estimaciones empiezan en {primero}, se esperaba {esperado + 1}")
    detalle = "; ".join(avisos) or f"Fuente y resultados al dia con la cobertura configurada ({esperado})"
    return {"estado": ALERTA if avisos else OK, "detalle": detalle, "ultimo_periodo_fuente": str(ultimo), "esperado": str(esperado)}


def calidad(actual: dict, anterior: dict | None, cfg: dict) -> dict:
    if anterior is None:
        return {"estado": SIN_REFERENCIA, "detalle": "La version vigente no tiene perfil de calidad para comparar", "actual": actual}
    umbral = cfg["monitoreo"]["cambio_filas_maximo"]
    avisos = []
    cambio_filas = actual["filas"] / anterior["filas"] - 1 if anterior["filas"] else np.inf
    if abs(cambio_filas) > umbral:
        avisos.append(f"las filas cambiaron {cambio_filas:+.1%} (de {anterior['filas']} a {actual['filas']}; umbral {umbral:.0%})")
    for campo, nombre in (("faltantes_conteo_usados", "conteos faltantes en tipos usados"), ("faltantes_totales", "faltantes totales"), ("claves_repetidas", "claves repetidas")):
        if actual[campo] > anterior[campo]:
            avisos.append(f"aumentaron los {nombre}: de {anterior[campo]} a {actual[campo]}")
    if actual["meses_con_datos"] < anterior["meses_con_datos"]:
        avisos.append(f"bajo la cobertura: de {anterior['meses_con_datos']} a {actual['meses_con_datos']} meses con datos")
    detalle = "; ".join(avisos) or "Sin cambios relevantes en faltantes, duplicados ni cobertura frente a la version vigente"
    return {"estado": ALERTA if avisos else OK, "detalle": detalle, "actual": actual, "anterior": anterior}


def resultados(estimaciones: pd.DataFrame, y: pd.Series, anteriores: pd.DataFrame | None, cfg: dict) -> dict:
    m = cfg["monitoreo"]
    est = estimaciones.set_index(pd.PeriodIndex(estimaciones["periodo"], freq="M"))["valor"]
    avisos = []
    invalidas = est[~np.isfinite(est) | (est < 0)]
    if len(invalidas):
        avisos.append(f"estimaciones negativas o no finitas en {[str(p) for p in invalidas.index]}")

    base = y.reindex(est.index - 12).to_numpy()
    interanual = pd.Series(est.to_numpy() / base - 1, index=est.index)
    altas = interanual[interanual.abs() > m["variacion_interanual_maxima"]]
    if len(altas):
        avisos.append("variacion interanual sobre el umbral " + ", ".join(f"{p} {v:+.1%}" for p, v in altas.items()))

    cambio_version = None
    if anteriores is not None and len(anteriores):
        previa = anteriores.set_index(pd.PeriodIndex(anteriores["periodo"], freq="M"))["valor"]
        comunes = est.index.intersection(previa.index)
        if len(comunes):
            relativo = (est[comunes] / previa[comunes] - 1).abs()
            cambio_version = float(relativo.max())
            if cambio_version > m["cambio_entre_versiones_maximo"]:
                avisos.append(f"cambio de hasta {cambio_version:.1%} frente a la version vigente en {[str(p) for p in relativo[relativo > m['cambio_entre_versiones_maximo']].index]}")
    detalle = "; ".join(avisos) or "Estimaciones finitas, no negativas y sin variaciones sobre los umbrales"
    return {
        "estado": ALERTA if avisos else OK,
        "detalle": detalle,
        "variacion_interanual_maxima_observada": float(interanual.abs().max()) if interanual.notna().any() else None,
        "cambio_maximo_frente_a_vigente": cambio_version,
    }
