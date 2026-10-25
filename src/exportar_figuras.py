"""Exporta a PNG las visualizaciones del tablero para el documento de diseno.

Uso:
    python -m src.exportar_figuras

Requiere kaleido y un Chrome/Chromium (kaleido lo busca solo; si no lo encuentra,
definir BROWSER_PATH con la ruta del ejecutable). Las figuras quedan en report/figures/.
Se usan exactamente las mismas funciones de src/graficas.py que la app.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from src.datos import TIPOS_COMPARABLES, agregar_periodo, filtrar
from src.estilo import ORDEN_VIA, SUPERFICIE
from src.graficas import (
    figura_error_horizonte,
    figura_error_modelos,
    figura_estacionalidad,
    figura_evolucion,
    figura_mapa_errores,
    figura_origen,
    figura_perfil_mensual,
    figura_pronostico,
    figura_recuperacion,
    figura_treemap,
    figura_tuneo,
    indice_recuperacion,
)
from src.modelos import METRICAS, ORDEN_MODELO, agregar_pronostico, tabla_metricas
from src.preparar_datos import OUT_PATH
from src.preparar_modelos import OUT_DIR

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "report" / "figures"

# Seleccion de ejemplo para mostrar el enlace entre graficas
EJEMPLO_PERIODO = "2019"
EJEMPLO_VIA = "Aérea"


def _para_documento(fig: go.Figure) -> go.Figure:
    """Fondo opaco y margenes amplios: fuera de Streamlit no hay contenedor que los ponga."""
    return fig.update_layout(paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE, margin=dict(l=20, r=30, t=50, b=20))


def _guardar(fig: go.Figure, nombre: str, alto: int | None = None) -> None:
    alto = alto or int(fig.layout.height or 420)
    _para_documento(fig).write_image(FIG_DIR / f"{nombre}.png", width=1100, height=alto, scale=2)
    print(f"  {nombre}.png")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(OUT_PATH)
    anios = (int(df["anio"].min()), int(df["anio"].max()))
    datos = filtrar(df, anios, TIPOS_COMPARABLES, ORDEN_VIA)

    # 1 y 2: evolucion -> origen
    d = datos.assign(periodo=agregar_periodo(datos["fecha"], "Año"))
    fig, _ = figura_evolucion(d, "Año")
    for traza in fig.data:
        traza.selectedpoints = [i for i, x in enumerate(traza.x) if x == EJEMPLO_PERIODO] if traza.name == EJEMPLO_VIA else []
    _guardar(fig, "viz1_evolucion_seleccion", 400)
    detalle = d[(d["periodo"] == EJEMPLO_PERIODO) & (d["via"] == EJEMPLO_VIA)]
    fig, _, _ = figura_origen(detalle, "pais", 10)
    _guardar(fig, "viz2_origen_seleccion", 420)

    # 3 y 4: estacionalidad -> perfil mensual
    _guardar(figura_estacionalidad(datos), "viz3_estacionalidad")
    ref = datos[datos["anio"].between(2015, 2019)].groupby("mes")["viajeros"].sum().div(5)
    _guardar(figura_perfil_mensual(datos, [2025], ref), "viz4_perfil_mensual")

    # 5 y 6: indice de recuperacion -> arbol de origenes
    _guardar(figura_recuperacion(indice_recuperacion(datos, "region", 2019, 8), 2019), "viz5_recuperacion")
    _guardar(figura_treemap(datos[datos["anio"] == 2025], 2), "viz6_treemap")

    # 7 y 8: pronostico -> error por modelo
    pron = pd.read_parquet(OUT_DIR / "pronosticos.parquet")
    pron["modelo"] = pd.Categorical(pron["modelo"], ORDEN_MODELO, ordered=True)
    series = pd.read_parquet(OUT_DIR / "series.parquet")
    total = pron[(pron["serie"] == "Total mensual") & (pron["modelo"] != "Referencia ingenua")]
    modelos = [m for m in ORDEN_MODELO if m in set(total["modelo"].astype(str))]
    hist = series[(series["serie"] == "Total mensual") & (series["conjunto"] == "Entrenamiento")]
    _guardar(figura_pronostico(hist, agregar_pronostico(total, "Mes"), modelos, "Mes", True), "viz7_pronostico")
    met = tabla_metricas(total, ["modelo"])
    _guardar(figura_error_modelos(met, "MAPE", METRICAS["MAPE"]), "viz8_error_modelos")

    # 9 y 10: mapa de errores -> error por anio
    m = tabla_metricas(pron, ["serie", "modelo"])
    tabla = m.pivot_table(index="serie", columns="modelo", values="MAPE", observed=False, dropna=False)
    tabla = tabla.reindex(index=list(dict.fromkeys(pron["serie"])), columns=ORDEN_MODELO)
    _guardar(figura_mapa_errores(tabla, "MAPE", METRICAS["MAPE"]), "viz9_mapa_errores")
    p = pron[pron["serie"] == "Total mensual"]
    por_anio = tabla_metricas(p.assign(anio=p["fecha"].dt.year), ["modelo", "anio"])
    _guardar(figura_error_horizonte(por_anio, "MAPE", METRICAS["MAPE"]), "viz10_error_horizonte")

    # 11: tuneo LSTM
    tuneo = pd.read_parquet(OUT_DIR / "tuneo_lstm.parquet")
    t = tuneo[tuneo["serie"] == "Total mensual"]
    _guardar(figura_tuneo(t, t.sort_values("val_RMSE")["modelo"].iloc[0]), "viz11_tuneo_lstm")

    print(f"Figuras en {FIG_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
