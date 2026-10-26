"""Paleta y estilo compartidos por todas las visualizaciones.

Regla del tablero: cada color significa SIEMPRE lo mismo en toda la aplicacion.
- Vias de ingreso -> paleta categorica (azul, naranja, aqua), en orden fijo.
  Las tres primeras posiciones de la paleta pasan la validacion de daltonismo
  (CVD) entre todos los pares, por eso alcanzan para las tres vias.
- Magnitudes (mapas de calor) -> una sola tonalidad de azul, de claro a oscuro.
- Estados (alerta, bien) -> colores reservados, nunca usados para series.
"""

from __future__ import annotations

import plotly.graph_objects as go

# Categoricos: vias de ingreso (orden fijo, el color sigue a la via, no al ranking)
COLORES_VIA = {
    "Aérea": "#2a78d6",
    "Terrestre": "#eb6834",
    "Marítima": "#1baf7a",
}
ORDEN_VIA = list(COLORES_VIA)

# Categoricos: modelos de pronostico (paginas de modelos). Hues distintos de las vias
# para que ningun color cambie de significado entre paginas. El valor real va en tinta negra
# y la referencia ingenua en gris (es una vara de medir, no un modelo candidato).
# Validado (scripts/validate_palette.js, todos los pares): CVD >= 16.2, vision normal >= 19.6.
# Magenta y amarillo quedan bajo 3:1 de contraste -> cada modelo lleva ademas un patron de
# linea propio (DASH_MODELO) y la tabla comparativa repite los valores.
COLORES_MODELO = {
    "Holt-Winters": "#6250d6",
    "SARIMA": "#e87ba4",
    "Prophet": "#eda100",
    "LSTM": "#008300",
    "Referencia ingenua": "#898781",
}
DASH_MODELO = {
    "Holt-Winters": "solid",
    "SARIMA": "dash",
    "Prophet": "dashdot",
    "LSTM": "longdash",
    "Referencia ingenua": "dot",
}
COLOR_REAL = "#161616"
COLOR_HISTORIA = "#898781"

# Secuencial (magnitud): azul claro -> oscuro
SECUENCIAL_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ESCALA_SECUENCIAL = [[i / (len(SECUENCIAL_AZUL) - 1), c] for i, c in enumerate(SECUENCIAL_AZUL)]

# Divergente (polaridad respecto a una base, p. ej. indice 2019 = 100):
# rojo = por debajo de la base, gris = igual, azul = por encima. Solo en mapas de calor con barra de color.
ESCALA_DIVERGENTE = [
    [0.0, "#d25757"],
    [0.25, "#e66767"],
    [0.5, "#f0efec"],
    [0.75, "#6da7ec"],
    [1.0, "#4a8ee0"],
]

# Estados reservados
ESTADO = {"bien": "#0ca30c", "alerta": "#fab219", "critico": "#d03b3b"}

# Tinta y superficies
SUPERFICIE = "#ffffff"
TINTA = "#161616"
TINTA_SECUNDARIA = "#525252"
TINTA_TENUE = "#6f6f6f"
CUADRICULA = "#e0e0e0"
EJE = "#c6c6c6"

# Misma familia que la interfaz (IBM Plex Sans); "IBM Plex Sans" es el nombre instalado que usa kaleido al exportar
FUENTE = 'PlexSans, "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif'


def aplicar_estilo(fig: go.Figure, alto: int = 420) -> go.Figure:
    """Ejes y cuadricula discretos para que el dato sea lo que resalta."""
    fig.update_layout(
        height=alto,
        font=dict(family=FUENTE, size=12, color=TINTA_SECUNDARIA),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            title_text="",
            font=dict(color=TINTA_SECUNDARIA),
        ),
        hoverlabel=dict(bgcolor="white", font=dict(family=FUENTE, color=TINTA), bordercolor=CUADRICULA),
        separators=".,",
        bargap=0.25,
    )
    fig.update_xaxes(
        showgrid=False, linecolor=EJE, automargin=True, tickfont=dict(color=TINTA_TENUE), title_font=dict(color=TINTA_SECUNDARIA)
    )
    fig.update_yaxes(
        automargin=True,
        gridcolor=CUADRICULA,
        zeroline=False,
        linecolor=EJE,
        tickfont=dict(color=TINTA_TENUE),
        title_font=dict(color=TINTA_SECUNDARIA),
    )
    return fig


MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def formato_numero(valor: float) -> str:
    """12345678 -> '12.3 M'; 45678 -> '45.7 mil'."""
    if abs(valor) >= 1_000_000:
        return f"{valor / 1_000_000:,.1f} M"
    if abs(valor) >= 1_000:
        return f"{valor / 1_000:,.1f} mil"
    return f"{valor:,.0f}"
