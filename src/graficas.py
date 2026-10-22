"""Construccion de las figuras del tablero.

Separadas de las paginas para que la app y src/exportar_figuras.py (figuras del
documento de diseno) usen exactamente la misma grafica.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.estilo import COLORES_VIA, CUADRICULA, ORDEN_VIA, SUPERFICIE, aplicar_estilo


def figura_evolucion(datos: pd.DataFrame, nivel: str) -> tuple[go.Figure, list[str]]:
    """Barras apiladas de viajeros por periodo y via.

    `datos` debe traer la columna `periodo`. Devuelve tambien el orden de las trazas
    (una por via), necesario para traducir `curve_number` de la seleccion a una via.
    """
    serie = datos.groupby(["periodo", "via"], observed=True)["viajeros"].sum().reset_index()
    periodos = sorted(serie["periodo"].unique())
    vias_trazas = [v for v in ORDEN_VIA if v in set(serie["via"])]

    fig = go.Figure()
    for via in vias_trazas:
        s = serie[serie["via"] == via]
        fig.add_bar(
            x=s["periodo"],
            y=s["viajeros"],
            name=via,
            marker=dict(color=COLORES_VIA[via], line=dict(color=SUPERFICIE, width=1 if nivel == "Mes" else 2)),
            hovertemplate=f"<b>%{{x}}</b><br>{via}: %{{y:,.0f}} viajeros<extra></extra>",
        )
    # Sin dragmode explicito: Streamlit solo habilita la seleccion por clic cuando el modo
    # de arrastre no es "select"/"lasso". La seleccion por caja queda en la barra de herramientas.
    fig.update_layout(barmode="stack", legend_traceorder="normal")
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=periodos, title_text=None, fixedrange=True)
    fig.update_yaxes(title_text="Viajeros", fixedrange=True)
    if nivel != "Año":
        # Con trimestres o meses, una etiqueta por año para que el eje se pueda leer
        inicios = [p for p in periodos if p.endswith(("-T1", "-01"))]
        fig.update_xaxes(tickvals=inicios, ticktext=[p[:4] for p in inicios], tickangle=0)
    aplicar_estilo(fig, alto=380)
    return fig, vias_trazas


def figura_origen(detalle: pd.DataFrame, dimension: str, top_n: int) -> tuple[go.Figure, pd.Series, pd.DataFrame]:
    """Top N categorias de `dimension` en barras horizontales apiladas por via.

    Devuelve la figura, los totales por categoria (todas, ordenadas) y el desglose por via.
    """
    desglose = detalle.groupby([dimension, "via"], observed=True)["viajeros"].sum().reset_index()
    totales = desglose.groupby(dimension, observed=True)["viajeros"].sum().sort_values(ascending=False)
    totales = totales[totales > 0]
    top = totales.head(top_n)
    orden_categorias = [str(c) for c in top.index[::-1]]  # la mayor queda arriba

    fig = go.Figure()
    for via in ORDEN_VIA:
        s = desglose[(desglose["via"] == via) & desglose[dimension].isin(top.index)]
        if s.empty:
            continue
        fig.add_bar(
            y=s[dimension].astype(str),
            x=s["viajeros"],
            name=via,
            orientation="h",
            marker=dict(color=COLORES_VIA[via], line=dict(color=SUPERFICIE, width=2)),
            hovertemplate=f"<b>%{{y}}</b><br>{via}: %{{x:,.0f}} viajeros<extra></extra>",
        )
    fig.update_layout(barmode="stack", legend_traceorder="normal")
    aplicar_estilo(fig, alto=max(320, 30 * len(top) + 80))
    # Barras horizontales: la cuadricula va en el eje de valores (x), no en el de categorias
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=orden_categorias, showgrid=False, title_text=None)
    fig.update_xaxes(title_text="Viajeros", showgrid=True, gridcolor=CUADRICULA)
    return fig, totales, desglose
