"""Componentes de interfaz compartidos por todas las paginas.

Todo lo visual que se repite (encabezado de pagina, tarjeta de grafica, indicadores,
hallazgos, barra de filtros) vive aqui para que el tablero hable un solo lenguaje visual.
Los contenedores usan `key`: Streamlit les agrega la clase `st-key-<key>` y el CSS de
`estilo_global` se engancha a esa clase.
"""

from __future__ import annotations

import html
from contextlib import contextmanager
from zlib import crc32

import pandas as pd
import streamlit as st

from src.datos import TIPOS_COMPARABLES
from src.estilo import ORDEN_VIA

# Distingue lo que se midio de lo que se interpreta o se estima (requisito de diseno)
TIPO_INFO = {
    "observado": ("Dato observado", "#1c5cab", "#e7f0fb"),
    "interpretacion": ("Interpretación", "#52514e", "#ecebe7"),
    "estimacion": ("Estimación de modelo", "#4a3aa7", "#ece9fb"),
}

FUENTE_DATOS = (
    "Base de migración, enero 2009 a junio 2026. Uso académico: no son cifras oficiales "
    "del INGUAT ni del Instituto Guatemalteco de Migración."
)

_CSS = """
<style>
/* ---------- estructura ---------- */
[data-testid="stMainBlockContainer"] { max-width: 1280px; padding-top: 2.2rem; padding-bottom: 4rem; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stHeader"] { background: transparent; }
h1, h2, h3 { letter-spacing: -0.01em; }

/* ---------- encabezado de pagina ---------- */
.op-eyebrow { font-size: .78rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #2a78d6; margin: 0 0 .35rem; }
.op-title { font-family: SourceSerif, Georgia, serif; font-weight: 600; font-size: 2.35rem; line-height: 1.12; color: #0b0b0b; margin: 0 0 .6rem; }
.op-lede { font-size: 1.08rem; line-height: 1.5; color: #3d3c3a; max-width: 62rem; margin: 0; }

/* ---------- tarjeta de grafica ---------- */
[class*="st-key-tarjeta-"] { background: #ffffff; box-shadow: 0 1px 2px rgba(13,54,107,.06); padding: 1.1rem 1.25rem 1rem !important; }
.op-chart-head { display: flex; gap: .9rem; align-items: flex-start; }
.op-num { font-family: SourceSerif, Georgia, serif; font-size: 1.9rem; font-weight: 600; line-height: 1; color: #0d366b; min-width: 1.6rem; }
.op-q { font-size: 1.16rem; font-weight: 700; line-height: 1.3; color: #0b0b0b; }
.op-sub { font-size: .93rem; color: #52514e; margin-top: .2rem; line-height: 1.45; }
.op-tag { display: inline-block; font-size: .7rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; padding: .12rem .55rem; border-radius: 999px; margin-top: .45rem; }
.op-hint { font-size: .84rem; color: #6b6a66; margin: .1rem 0 0; }
.op-hint b { color: #3d3c3a; }

/* ---------- indicadores ---------- */
.op-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: .9rem; margin: .4rem 0 .2rem; }
.op-kpi { background: #ffffff; border: 1px solid #dedcd5; border-top: 3px solid #0d366b; border-radius: .5rem; padding: .85rem 1rem .8rem; }
.op-kpi .l { font-size: .74rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #6b6a66; }
.op-kpi .v { font-family: SourceSerif, Georgia, serif; font-size: 2.05rem; font-weight: 600; line-height: 1.1; color: #0d366b; margin-top: .3rem; }
.op-kpi .c { font-size: .86rem; color: #52514e; margin-top: .25rem; line-height: 1.35; }
.op-kpi .c .neg { color: #b23a3a; font-weight: 700; }
.op-kpi .c .pos { color: #0a7a0a; font-weight: 700; }

/* ---------- hallazgos ---------- */
[class*="st-key-hallazgo-"] { border-radius: .5rem; padding: .8rem 1rem .5rem !important; gap: .25rem; }
[class*="st-key-hallazgo-observado"] { background: #eef4fc; border-left: 3px solid #2a78d6; }
[class*="st-key-hallazgo-interpretacion"] { background: #f2f1ed; border-left: 3px solid #898781; }
[class*="st-key-hallazgo-estimacion"] { background: #f1effc; border-left: 3px solid #6250d6; }
.op-hl { font-size: .72rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }

/* ---------- barra de filtros ---------- */
[class*="st-key-filtros-"] { background: #f0efec; border-radius: .6rem; padding: .7rem 1rem .2rem !important; }

/* ---------- tarjetas de navegacion ---------- */
[class*="st-key-nav-"] { background: #ffffff; min-height: 15.5rem; justify-content: space-between; }
.op-nav-k { font-size: .72rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: #2a78d6; }
.op-nav-t { font-family: SourceSerif, Georgia, serif; font-size: 1.3rem; font-weight: 600; color: #0b0b0b; margin: .15rem 0 .35rem; }
.op-nav-d { font-size: .92rem; color: #52514e; line-height: 1.45; }
.op-nav-q { font-size: .86rem; color: #3d3c3a; margin: .55rem 0 .1rem; padding-left: 1rem; }
.op-nav-q li { margin-bottom: .2rem; }

/* ---------- barra lateral ---------- */
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { font-size: .78rem; line-height: 1.45; }
</style>
"""


def _clave(*partes: object) -> str:
    """Clave estable entre ejecuciones para contenedores con estilo propio."""
    return f"{crc32('|'.join(map(str, partes)).encode()):x}"


def estilo_global() -> None:
    st.html(_CSS)


def encabezado_pagina(seccion: str, titulo: str, bajada: str) -> None:
    st.html(
        f'<div class="op-eyebrow">{html.escape(seccion)}</div>'
        f'<h1 class="op-title">{html.escape(titulo)}</h1>'
        f'<p class="op-lede">{bajada}</p>'
    )


def _etiqueta_html(tipo: str) -> str:
    texto, color, fondo = TIPO_INFO[tipo]
    return f'<span class="op-tag" style="color:{color};background:{fondo}">{texto}</span>'


@contextmanager
def tarjeta_grafica(numero: int, pregunta: str, tipo: str, para_que: str, como_leer: str, interaccion: str | None = None):
    """Contenedor de una visualizacion: pregunta, una linea de proposito y, a peticion,
    la explicacion de como leerla (divulgacion progresiva)."""
    with st.container(border=True, key=f"tarjeta-{numero}"):
        izq, der = st.columns([0.84, 0.16], vertical_alignment="top")
        izq.html(
            f'<div class="op-chart-head"><div class="op-num">{numero}</div><div>'
            f'<div class="op-q">{html.escape(pregunta)}</div>'
            f'<div class="op-sub">{para_que}</div>{_etiqueta_html(tipo)}</div></div>'
        )
        with der.popover("Cómo leerla", icon=":material/menu_book:", width="stretch"):
            st.markdown(como_leer)
        if interaccion:
            st.html(f'<p class="op-hint">{interaccion}</p>')
        yield


def indicadores(items: list[tuple[str, str, str]]) -> None:
    """Fila de indicadores: (etiqueta, valor, contexto). El contexto admite <span class="neg|pos">."""
    celdas = "".join(
        f'<div class="op-kpi"><div class="l">{html.escape(l)}</div><div class="v">{html.escape(v)}</div><div class="c">{c}</div></div>'
        for l, v, c in items
    )
    st.html(f'<div class="op-kpis">{celdas}</div>')


def hallazgo(tipo: str, texto: str) -> None:
    """Recuadro de texto con el tipo de informacion explicito (observado, interpretacion, estimacion)."""
    etiqueta, color, _ = TIPO_INFO[tipo]
    with st.container(key=f"hallazgo-{tipo}-{_clave(texto)}"):
        st.html(f'<div class="op-hl" style="color:{color}">{etiqueta}</div>')
        st.markdown(texto)


@contextmanager
def barra_filtros(nombre: str):
    with st.container(key=f"filtros-{nombre}"):
        yield


def selector_graficas(opciones: dict[str, str], key: str) -> set[str]:
    """Permite al usuario elegir que graficas de la pagina ver. Devuelve las claves visibles."""
    elegidas = st.pills(
        "Gráficas visibles",
        list(opciones),
        format_func=lambda k: opciones[k],
        selection_mode="multi",
        default=list(opciones),
        key=key,
        help="Oculte las gráficas que no necesite para concentrarse en una pregunta.",
    )
    if not elegidas:
        st.info("No hay gráficas seleccionadas. Active al menos una en **Gráficas visibles**.", icon=":material/visibility_off:")
    return set(elegidas)


def filtros_viajeros(df: pd.DataFrame, key: str, extra: int = 0) -> tuple[tuple[int, int], list[str], list[str], list]:
    """Filtros comunes (anios, tipo de viajero, via) y `extra` columnas libres en la misma fila."""
    anio_min, anio_max = int(df["anio"].min()), int(df["anio"].max())
    cols = st.columns([1.0, 1.35, 1.6] + [1.25] * extra, gap="medium")
    anios = cols[0].slider("Años", anio_min, anio_max, (anio_min, anio_max), key=f"{key}_anios")
    tipos_disp = sorted(df["tipo"].unique())
    tipos = cols[1].multiselect(
        "Tipo de viajero",
        tipos_disp,
        default=[t for t in TIPOS_COMPARABLES if t in tipos_disp],
        key=f"{key}_tipos",
        help="Por defecto, turistas y excursionistas: los únicos tipos registrados de la misma forma en todo 2009-2026.",
    )
    vias = cols[2].multiselect("Vía de ingreso", ORDEN_VIA, default=ORDEN_VIA, key=f"{key}_vias")
    return anios, tipos, vias, cols[3:]


def sin_datos(mensaje: str) -> None:
    st.warning(mensaje, icon=":material/search_off:")
