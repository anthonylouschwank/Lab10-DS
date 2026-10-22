"""Exporta a PNG las visualizaciones del tablero para el documento de diseno.

Uso:
    python -m src.exportar_figuras

Requiere kaleido (y Chrome instalado). Las figuras quedan en report/figures/.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from src.datos import TIPOS_COMPARABLES, agregar_periodo, filtrar
from src.estilo import SUPERFICIE
from src.graficas import figura_evolucion, figura_origen
from src.preparar_datos import OUT_PATH

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "report" / "figures"

# Seleccion de ejemplo para mostrar el enlace entre graficas
EJEMPLO_PERIODO = "2019"
EJEMPLO_VIA = "Aérea"


def _para_documento(fig: go.Figure) -> go.Figure:
    """Fondo opaco y margenes amplios: fuera de Streamlit no hay contenedor que los ponga."""
    return fig.update_layout(paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE, margin=dict(l=20, r=30, t=50, b=20))


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(OUT_PATH)
    anios = (int(df["anio"].min()), int(df["anio"].max()))
    datos = filtrar(df, anios, TIPOS_COMPARABLES, ["Aérea", "Terrestre", "Marítima"])

    for nivel, nombre in [("Año", "anual"), ("Mes", "mensual")]:
        d = datos.assign(periodo=agregar_periodo(datos["fecha"], nivel))
        fig, _ = figura_evolucion(d, nivel)
        _para_documento(fig).write_image(FIG_DIR / f"viz1_evolucion_{nombre}.png", width=1100, height=400, scale=2)

    # Grafica 1 con una barra seleccionada (el resto se atenua, igual que en la app)
    d = datos.assign(periodo=agregar_periodo(datos["fecha"], "Año"))
    fig, vias_trazas = figura_evolucion(d, "Año")
    for traza in fig.data:
        traza.selectedpoints = [i for i, x in enumerate(traza.x) if x == EJEMPLO_PERIODO] if traza.name == EJEMPLO_VIA else []
    _para_documento(fig).write_image(FIG_DIR / "viz1_evolucion_seleccion.png", width=1100, height=400, scale=2)

    fig, _, _ = figura_origen(datos, "region", 10)
    _para_documento(fig).write_image(FIG_DIR / "viz2_origen_todo.png", width=1100, height=420, scale=2)

    detalle = d[(d["periodo"] == EJEMPLO_PERIODO) & (d["via"] == EJEMPLO_VIA)]
    fig, _, _ = figura_origen(detalle, "pais", 10)
    _para_documento(fig).write_image(FIG_DIR / "viz2_origen_seleccion.png", width=1100, height=420, scale=2)

    print(f"Figuras en {FIG_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
