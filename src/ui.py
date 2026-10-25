"""Piezas de interfaz repetidas en todas las paginas.

Mantenerlas en un solo lugar asegura que los encabezados, los filtros, las etiquetas
"Observado / Estimación" y el selector de graficas se vean y se comporten igual en todo el tablero.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.datos import TIPOS_COMPARABLES
from src.estilo import ORDEN_VIA

# Distingue lo que se midio de lo que se interpreta o se estima (requisito de diseno)
TIPO_INFO = {
    "observado": ("Dato observado", "blue", ":material/visibility:"),
    "interpretacion": ("Interpretación", "gray", ":material/lightbulb:"),
    "estimacion": ("Estimación de modelo", "violet", ":material/query_stats:"),
}


def etiqueta(tipo: str) -> None:
    texto, color, icono = TIPO_INFO[tipo]
    st.badge(texto, color=color, icon=icono)


def encabezado_grafica(numero: int, pregunta: str, tipo: str, que_muestra: str, para_que: str) -> None:
    """Titulo como pregunta de gestion + que muestra + para que le sirve a un directivo."""
    st.subheader(f"{numero}. {pregunta}")
    etiqueta(tipo)
    st.markdown(f"**Qué muestra:** {que_muestra}  \n**Para qué sirve:** {para_que}")


def selector_graficas(opciones: dict[str, str], key: str) -> set[str]:
    """Permite al usuario elegir que graficas de la pagina ver. Devuelve las claves visibles."""
    elegidas = st.pills(
        "Gráficas visibles",
        list(opciones),
        format_func=lambda k: opciones[k],
        selection_mode="multi",
        default=list(opciones),
        key=key,
        help="Oculta las gráficas que no necesites para enfocarte en una pregunta.",
    )
    if not elegidas:
        st.info("No hay gráficas seleccionadas. Elige al menos una en **Gráficas visibles**.", icon=":material/visibility_off:")
    return set(elegidas)


def filtros_viajeros(df: pd.DataFrame, key: str, con_vias: bool = True) -> tuple[tuple[int, int], list[str], list[str]]:
    """Filtros comunes: rango de anios, tipo de viajero y via de ingreso."""
    anio_min, anio_max = int(df["anio"].min()), int(df["anio"].max())
    cols = st.columns(3 if con_vias else 2)
    anios = cols[0].slider("Años", anio_min, anio_max, (anio_min, anio_max), key=f"{key}_anios")
    tipos_disp = sorted(df["tipo"].unique())
    tipos = cols[1].multiselect(
        "Tipo de viajero",
        tipos_disp,
        default=[t for t in TIPOS_COMPARABLES if t in tipos_disp],
        key=f"{key}_tipos",
        help="Por defecto solo turistas y excursionistas: son los únicos tipos registrados de forma comparable en todo 2009-2026.",
    )
    vias = ORDEN_VIA
    if con_vias:
        vias = cols[2].multiselect("Vía de ingreso", ORDEN_VIA, default=ORDEN_VIA, key=f"{key}_vias")
    return anios, tipos, vias


def sin_datos(mensaje: str) -> None:
    st.warning(mensaje, icon=":material/search_off:")


def nota_fuente() -> None:
    st.caption("Fuente: base de migración 2009-junio 2026 (uso académico; no son cifras oficiales del INGUAT ni del IGM).")
