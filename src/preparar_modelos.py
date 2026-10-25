"""Empaqueta los resultados de los Laboratorios 1 y 2 para el tablero.

No entrena modelos. Lee lo que ya produjo el repositorio de los laboratorios
(https://github.com/Isabella1911/DM-Laboratorio-1.-Series-de-Tiempo):

- Laboratorio 1: `outputs/parte1/series/*` (train/test) y `outputs/parte2/pronosticos/*`
  (pronosticos de prueba). `outputs/` no esta versionado en ese repositorio; se genera con
  `L.run()` y `M.ejecutar_parte2()` segun su README.
- Laboratorio 2: `resultados/predicciones_serie_{1,2}.csv` (LSTM) y `resultados/tuneo_serie_*.csv`.

De cada familia del Laboratorio 1 se toma la variante con menor RMSE de prueba, que es el
mismo criterio con el que el Laboratorio 1 eligio su mejor modelo por serie, con una
salvedad: se descartan primero las variantes cuyo pronostico tiene meses invalidos (NaN).
En San Cristobal, el SARIMA(1,1,1)x(1,0,1,12) elegido por el Lab 1 solo produjo 10 de 63
meses validos, asi que su RMSE no era comparable con el de los demas modelos.

Uso:
    python -m src.preparar_modelos RUTA_REPO_LABORATORIOS

Salida en data/modelos/ (parquet versionado, la app no necesita el repo de los labs).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "modelos"

SERIES = {
    "total_mensual": "Total mensual",
    "via_aerea": "Vía Aérea",
    "via_terrestre": "Vía Terrestre",
    "via_maritima": "Vía Marítima",
    "frontera_01_la_aurora": "Frontera La Aurora (aérea)",
    "frontera_07_valle_nuevo": "Frontera Valle Nuevo (terrestre)",
    "frontera_09_san_cristobal": "Frontera San Cristóbal (terrestre)",
}

# Prefijo del archivo de pronostico -> familia mostrada en el tablero
FAMILIAS = {
    "arima": "SARIMA",
    "holtwinters": "Holt-Winters",
    "prophet": "Prophet",
    "seasonalnaive": "Referencia ingenua",
}

LSTM = {  # serie del Lab 2 -> (archivo de predicciones, archivo de tuneo)
    "total_mensual": ("predicciones_serie_1.csv", "tuneo_serie_1.csv"),
    "frontera_01_la_aurora": ("predicciones_serie_2.csv", "tuneo_serie_2.csv"),
}


def _variante(slug_modelo: str) -> str:
    """'arima_1_1_1_x_0_0_1_12' -> 'ARIMA(1,1,1)x(0,0,1,12)'; legible para el glosario."""
    m = re.fullmatch(r"arima_(\d)_(\d)_(\d)_x_(\d)_(\d)_(\d)_12", slug_modelo)
    if m:
        a = m.groups()
        return f"SARIMA({a[0]},{a[1]},{a[2]})x({a[3]},{a[4]},{a[5]},12)"
    m = re.fullmatch(r"holtwinters_trend_(\w+)_seasonal_(\w+)_damped_(\w+)", slug_modelo)
    if m:
        est = "multiplicativa" if m.group(2) == "mul" else "aditiva"
        amort = ", tendencia amortiguada" if m.group(3) == "true" else ""
        return f"Holt-Winters (estacionalidad {est}{amort})"
    return {"prophet": "Prophet (con regresor de pandemia)", "seasonalnaive": "Mismo mes del último año de entrenamiento"}.get(
        slug_modelo, slug_modelo
    )


def _rmse(real: pd.Series, pred: pd.Series) -> float:
    m = real.notna() & pred.notna()
    return float(np.sqrt(np.mean((real[m] - pred[m]) ** 2))) if m.any() else np.nan


def preparar(repo: Path) -> None:
    series_dir = repo / "outputs" / "parte1" / "series"
    pron_dir = repo / "outputs" / "parte2" / "pronosticos"
    res_dir = repo / "resultados"
    for p in (series_dir, pron_dir, res_dir):
        if not p.exists():
            sys.exit(f"No existe {p}. Ejecute primero el pipeline del Laboratorio 1 (ver docstring).")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- series observadas con su particion
    historia = []
    for slug, nombre in SERIES.items():
        for parte, etiqueta in (("train", "Entrenamiento"), ("test", "Prueba")):
            s = pd.read_csv(series_dir / f"{slug}_{parte}.csv", parse_dates=["fecha"])
            historia.append(s.assign(serie=nombre, conjunto=etiqueta)[["serie", "fecha", "conjunto", "valor"]])
    pd.concat(historia).to_parquet(OUT_DIR / "series.parquet", index=False)

    # ---- pronosticos del Lab 1: mejor variante por familia
    filas = []
    for slug, nombre in SERIES.items():
        candidatos: dict[str, list[tuple[float, str, pd.DataFrame]]] = {}
        for archivo in sorted(pron_dir.glob(f"pronostico_{slug}_*.csv")):
            slug_modelo = archivo.stem.removeprefix(f"pronostico_{slug}_")
            familia = next((f for pref, f in FAMILIAS.items() if slug_modelo.startswith(pref)), None)
            if familia is None:  # suavizamiento exponencial sin estacionalidad: no se muestra
                continue
            df = pd.read_csv(archivo, parse_dates=["fecha"])
            incompleto = bool(df["prediccion"].isna().any())
            candidatos.setdefault(familia, []).append((incompleto, _rmse(df["real"], df["prediccion"]), slug_modelo, df))
        for familia, lista in candidatos.items():
            # Sin datos de prueba (via maritima) el RMSE es NaN: se conserva el primero (menor AIC en el Lab 1)
            lista.sort(key=lambda t: (t[0], np.isnan(t[1]), t[1]))
            _, _, slug_modelo, df = lista[0]
            for col in ("limite_inferior", "limite_superior"):
                if col not in df:
                    df[col] = np.nan
            filas.append(df.assign(serie=nombre, modelo=familia, variante=_variante(slug_modelo), laboratorio="Lab 1"))

    # ---- LSTM del Lab 2
    for slug, (pred_csv, _) in LSTM.items():
        df = pd.read_csv(res_dir / pred_csv, parse_dates=["fecha"])
        df = df.rename(columns={"Real": "real", "Prediccion_LSTM": "prediccion"})
        df["limite_inferior"] = np.nan
        df["limite_superior"] = np.nan
        filas.append(
            df.assign(serie=SERIES[slug], modelo="LSTM", variante="LSTM (1 capa, 32 unidades, ventana de 6 meses)", laboratorio="Lab 2")
        )

    pron = pd.concat(filas, ignore_index=True)[
        ["serie", "modelo", "variante", "laboratorio", "fecha", "real", "prediccion", "limite_inferior", "limite_superior"]
    ]
    pron.to_parquet(OUT_DIR / "pronosticos.parquet", index=False)

    # ---- tuneo LSTM (curva de validacion por configuracion)
    tuneo = []
    for slug, (_, tuneo_csv) in LSTM.items():
        t = pd.read_csv(res_dir / tuneo_csv)
        tuneo.append(t.assign(serie=SERIES[slug]))
    pd.concat(tuneo).to_parquet(OUT_DIR / "tuneo_lstm.parquet", index=False)

    print(f"{len(pron):,} filas de pronostico, {pron.groupby(['serie', 'modelo']).ngroups} combinaciones serie-modelo -> {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    preparar(Path(sys.argv[1]).resolve())
