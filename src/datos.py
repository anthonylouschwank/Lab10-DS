"""Carga de datos con cache para el tablero."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.preparar_datos import OUT_PATH, RAW_PATH, preparar

# Solo turistas y excursionistas son comparables en todo 2009-2026 (criterio del Lab 1)
TIPOS_COMPARABLES = ["Turista", "Excursionista"]

DIMENSIONES = {
    "Región de origen": "region",
    "País de origen": "pais",
    "Frontera / puesto de ingreso": "frontera",
    "Región OMT": "region_omt",
}

NIVELES_TIEMPO = ["Año", "Trimestre", "Mes"]


@st.cache_data(show_spinner="Cargando datos de viajeros...")
def cargar_viajeros(path: Path = OUT_PATH) -> pd.DataFrame:
    if not path.exists():
        if not RAW_PATH.exists():
            raise FileNotFoundError(f"No se encontró la base en {RAW_PATH}")
        return preparar()
    return pd.read_parquet(path)


def filtrar(df: pd.DataFrame, anios: tuple[int, int], tipos: list[str], vias: list[str]) -> pd.DataFrame:
    return df[df["anio"].between(*anios) & df["tipo"].isin(tipos) & df["via"].isin(vias)]


def agregar_periodo(fechas: pd.Series, nivel: str) -> pd.Series:
    """Etiqueta ordenable para el nivel de detalle temporal elegido."""
    if nivel == "Año":
        return fechas.dt.year.astype(str)
    if nivel == "Trimestre":
        return fechas.dt.year.astype(str) + "-T" + fechas.dt.quarter.astype(str)
    return fechas.dt.strftime("%Y-%m")
