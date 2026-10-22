"""Convierte la base de migracion (xlsx) a un parquet liviano para el tablero.

Uso:
    python -m src.preparar_datos

Leer el Excel (161k filas) tarda varios segundos; el parquet carga en milisegundos.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "Base_Migracion_2009-2026jun.xlsx"
OUT_PATH = ROOT / "data" / "procesados" / "viajeros.parquet"
SHEET_NAME = "Datos"

COLUMNAS = {
    "Año": "anio",
    "Mes cod": "mes",
    "Vía": "via",
    "Frontera": "frontera",
    "País": "pais",
    "Región dos": "region",
    "Regiones OMT": "region_omt",
    "Tipo de Viajero": "tipo",
    "Viajero": "viajeros",
}


def preparar(raw_path: Path = RAW_PATH, out_path: Path = OUT_PATH) -> pd.DataFrame:
    df = pd.read_excel(raw_path, sheet_name=SHEET_NAME, usecols=list(COLUMNAS))
    df = df.rename(columns=COLUMNAS)

    df["anio"] = df["anio"].astype("int16")
    df["mes"] = df["mes"].astype("int8")
    df["fecha"] = pd.to_datetime(dict(year=df["anio"], month=df["mes"], day=1))
    df["viajeros"] = pd.to_numeric(df["viajeros"], errors="coerce").fillna(0)

    for col in ["via", "frontera", "pais", "region", "region_omt", "tipo"]:
        # La fuente marca algunas categorias vacias con "0"
        df[col] = df[col].fillna("Sin dato").astype(str).str.strip().replace({"0": "Sin dato", "": "Sin dato"}).astype("category")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    return df


if __name__ == "__main__":
    datos = preparar()
    print(f"{len(datos):,} filas -> {OUT_PATH.relative_to(ROOT)}")
    print(f"Rango: {datos['fecha'].min():%Y-%m} a {datos['fecha'].max():%Y-%m}")
    for col in ["via", "tipo", "region"]:
        print(f"{col}: {sorted(datos[col].unique())}")
