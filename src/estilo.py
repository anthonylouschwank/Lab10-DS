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

# Categoricos: modelos de pronostico (pagina de modelos). Hues distintos de las vias
# para que ningun color cambie de significado entre paginas. El valor real va en tinta negra.
COLORES_MODELO = {
    "Holt-Winters": "#6250d6",
    "SARIMA": "#e87ba4",
    "LSTM": "#008300",
}

# Secuencial (magnitud): azul claro -> oscuro
SECUENCIAL_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# Estados reservados
ESTADO = {"bien": "#0ca30c", "alerta": "#fab219", "critico": "#d03b3b"}

# Tinta y superficies
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_TENUE = "#898781"
CUADRICULA = "#e1e0d9"
EJE = "#c3c2b7"

# Misma familia que la interfaz de Streamlit (Source Sans), con respaldo al sans del sistema
FUENTE = '"Source Sans Pro", "Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif'


def aplicar_estilo(fig: go.Figure, alto: int = 420) -> go.Figure:
    """Ejes y cuadricula discretos para que el dato sea lo que resalta."""
    fig.update_layout(
        height=alto,
        font=dict(family=FUENTE, size=13, color=TINTA_SECUNDARIA),
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


def formato_numero(valor: float) -> str:
    """12345678 -> '12.3 M'; 45678 -> '45.7 mil'."""
    if abs(valor) >= 1_000_000:
        return f"{valor / 1_000_000:,.1f} M"
    if abs(valor) >= 1_000:
        return f"{valor / 1_000:,.1f} mil"
    return f"{valor:,.0f}"
