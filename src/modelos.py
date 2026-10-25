"""Resultados de los modelos de los Laboratorios 1 y 2 (generados por src/preparar_modelos.py).

Aqui no se entrena nada: solo se leen pronosticos ya calculados y se resumen sus errores.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.preparar_modelos import OUT_DIR

ORDEN_MODELO = ["Holt-Winters", "SARIMA", "Prophet", "LSTM", "Referencia ingenua"]

METRICAS = {
    "MAPE": "Error porcentual promedio (MAPE, %)",
    "MAE": "Error promedio en viajeros (MAE)",
    "RMSE": "Error que penaliza fallos grandes (RMSE)",
}

DESCRIPCION_MODELO = {
    "Holt-Winters": "Proyecta el nivel, la tendencia y el patrón de cada mes del año a partir de promedios que dan más peso a los meses recientes.",
    "SARIMA": "Modelo estadístico que usa los valores y errores de meses anteriores, incluyendo el mismo mes del año previo.",
    "Prophet": "Separa tendencia y estacionalidad anual; incluye una variable que marca el periodo de pandemia (mar-2020 a dic-2021).",
    "LSTM": "Red neuronal (Laboratorio 2) que aprende de ventanas de 6 meses y pronostica cada mes usando sus propias predicciones anteriores.",
    "Referencia ingenua": "Repite los valores del último año antes del corte. Sirve de vara mínima: un modelo útil debería superarla.",
}


@st.cache_data(show_spinner="Cargando resultados de los modelos...")
def cargar_pronosticos() -> pd.DataFrame:
    df = pd.read_parquet(OUT_DIR / "pronosticos.parquet")
    df["modelo"] = pd.Categorical(df["modelo"], ORDEN_MODELO, ordered=True)
    return df


@st.cache_data
def cargar_series() -> pd.DataFrame:
    return pd.read_parquet(OUT_DIR / "series.parquet")


@st.cache_data
def cargar_tuneo() -> pd.DataFrame:
    return pd.read_parquet(OUT_DIR / "tuneo_lstm.parquet")


def calcular_metricas(df: pd.DataFrame) -> pd.Series:
    """Misma formula del Laboratorio 1: MAPE ignora los meses con valor real cero."""
    d = df.dropna(subset=["real", "prediccion"])
    if d.empty:
        return pd.Series({"MAE": np.nan, "RMSE": np.nan, "MAPE": np.nan, "meses": 0})
    error = d["real"] - d["prediccion"]
    nz = d["real"] != 0
    mape = float((error[nz] / d.loc[nz, "real"]).abs().mean() * 100) if nz.any() else np.nan
    return pd.Series(
        {"MAE": error.abs().mean(), "RMSE": float(np.sqrt((error**2).mean())), "MAPE": mape, "meses": len(d)}
    )


def tabla_metricas(pron: pd.DataFrame, por: list[str]) -> pd.DataFrame:
    return pron.groupby(por, observed=True).apply(calcular_metricas, include_groups=False).reset_index()


def agregar_pronostico(pron: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Suma real y prediccion al nivel temporal elegido (los limites de confianza no se suman)."""
    if nivel == "Mes":
        return pron.assign(periodo=pron["fecha"])
    regla = "QS" if nivel == "Trimestre" else "YS"
    agg = (
        pron.groupby(["modelo", pd.Grouper(key="fecha", freq=regla)], observed=True)[["real", "prediccion"]]
        .sum(min_count=1)
        .reset_index()
    )
    return agg.assign(periodo=agg["fecha"], limite_inferior=np.nan, limite_superior=np.nan)
