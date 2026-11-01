"""Lectura de la version aprobada del pipeline (Laboratorio 11) para el tablero.

El tablero solo lee archivos de salidas/: nunca ajusta el procedimiento, asi que cambiar un filtro
no recalcula nada. salidas/vigente.json dice que version mostrar; OBS_SALIDAS cambia la carpeta.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent.parent
REQUERIDOS = ["estimaciones.parquet", "observados.parquet", "metricas.json", "config.yaml"]


def carpeta_salidas() -> Path:
    valor = os.environ.get("OBS_SALIDAS")
    return Path(valor) if valor and Path(valor).is_absolute() else ROOT / (valor or "salidas")


def leer_vigente() -> tuple[dict | None, Path | None]:
    """Version aprobada que debe mostrar el tablero; (None, None) si no hay una completa."""
    salidas = carpeta_salidas()
    archivo = salidas / "vigente.json"
    if not archivo.exists():
        return None, None
    info = json.loads(archivo.read_text(encoding="utf-8"))
    carpeta = salidas / info["ruta"]
    if not all((carpeta / a).exists() for a in REQUERIDOS):
        return None, None
    return info, carpeta


@st.cache_data(show_spinner=False)
def cargar_version(carpeta: str, id_ejecucion: str) -> dict:
    """Archivos de una version. La cache depende del id: al publicar o restaurar se lee la nueva."""
    c = Path(carpeta)
    leer_json = lambda nombre: json.loads((c / nombre).read_text(encoding="utf-8")) if (c / nombre).exists() else None  # noqa: E731
    version = {
        "estimaciones": pd.read_parquet(c / "estimaciones.parquet"),
        "observados": pd.read_parquet(c / "observados.parquet"),
        "evaluacion": pd.read_parquet(c / "evaluacion.parquet") if (c / "evaluacion.parquet").exists() else None,
        "metricas": leer_json("metricas.json"),
        "monitoreo": leer_json("monitoreo.json"),
        "config": yaml.safe_load((c / "config.yaml").read_text(encoding="utf-8")),
    }
    for nombre in ("estimaciones", "observados", "evaluacion"):
        if version[nombre] is not None:
            version[nombre]["fecha"] = pd.PeriodIndex(version[nombre]["periodo"], freq="M").to_timestamp()
    return version
