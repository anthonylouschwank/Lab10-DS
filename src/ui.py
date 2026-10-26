"""Componentes de interfaz del tablero.

El lenguaje visual sigue la estructura de IBM Carbon para productos de datos: escala de
grises g10, mosaicos blancos de borde fino, tipografia IBM Plex Sans, etiquetas pequenas
y la explicacion de cada grafica detras de un icono de informacion. Los contenedores
usan `key`; Streamlit les agrega la clase `st-key-<key>` y el CSS se engancha a ella.
"""

from __future__ import annotations

import html
from contextlib import contextmanager
from zlib import crc32

import pandas as pd
import streamlit as st

from src.datos import TIPOS_COMPARABLES
from src.estilo import ORDEN_VIA

# Etiqueta, color de texto y fondo (tags de Carbon: blue 20, gray 20, purple 20)
TIPO_INFO = {
    "observado": ("Observado", "#0043ce", "#d0e2ff"),
    "interpretacion": ("Interpretación", "#393939", "#e0e0e0"),
    "estimacion": ("Estimado", "#6929c4", "#e8daff"),
}

FUENTE_DATOS = "Base de migración, ene 2009 – jun 2026. Uso académico; no son cifras oficiales."

MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

_CSS = """
<style>
[data-testid="stMainBlockContainer"] { max-width: 1440px; padding: 1.25rem 2rem 3rem; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebarContent"] { padding-top: .25rem; }
[data-testid="stVerticalBlock"] { gap: .75rem; }

/* encabezado de pagina */
.ot-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 2rem; padding: .25rem 0 .75rem; }
.ot-crumb { font-size: .75rem; color: #6f6f6f; margin-bottom: .2rem; }
.ot-h1 { font-size: 1.75rem; font-weight: 400; line-height: 1.25; color: #161616; margin: 0; }
.ot-desc { font-size: .875rem; color: #525252; margin: .35rem 0 0; max-width: 56rem; line-height: 1.45; }
.ot-meta { font-size: .75rem; color: #6f6f6f; text-align: right; white-space: nowrap; line-height: 1.6; }
.ot-meta b { color: #161616; font-weight: 500; }

/* mosaicos */
[class*="st-key-tile-"], [class*="st-key-filtros-"] { background: #ffffff; border: 1px solid #e0e0e0; padding: 1rem 1rem .75rem !important; gap: .5rem; }
[class*="st-key-filtros-"] { padding: .75rem 1rem .25rem !important; }
.ot-tt { font-size: .9375rem; font-weight: 600; color: #161616; line-height: 1.3; }
.ot-ts { font-size: .75rem; color: #6f6f6f; margin-top: .15rem; line-height: 1.4; }
.ot-tags { display: flex; gap: .4rem; justify-content: flex-end; align-items: center; flex-wrap: wrap; padding-top: .1rem; }
.ot-tag { font-size: .6875rem; line-height: 1.1rem; padding: 0 .5rem; border-radius: 1rem; white-space: nowrap; }
[class*="st-key-tile-"] [data-testid="stPopover"] button { border: none; background: transparent; min-height: 1.75rem; padding: 0 .25rem; color: #525252; }
[class*="st-key-tile-"] [data-testid="stPopover"] button:hover { background: #e8e8e8; color: #161616; }
[class*="st-key-tile-"] [data-testid="stPopover"] button div[aria-hidden="true"] { display: none; }
.ot-chip { font-size: .6875rem; line-height: 1.1rem; padding: 0 .5rem; background: #161616; color: #ffffff; white-space: nowrap; max-width: 22rem; overflow: hidden; text-overflow: ellipsis; }

/* indicadores */
.ot-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: .75rem; }
.ot-kpi { background: #ffffff; border: 1px solid #e0e0e0; padding: .9rem 1rem .8rem; display: flex; flex-direction: column; gap: .2rem; }
.ot-kpi .l { font-size: .75rem; color: #525252; }
.ot-kpi .row { display: flex; justify-content: space-between; align-items: flex-end; gap: .75rem; }
.ot-kpi .v { font-size: 1.875rem; font-weight: 300; color: #161616; line-height: 1.15; font-variant-numeric: tabular-nums; letter-spacing: -.01em; }
.ot-kpi .d { font-size: .75rem; color: #525252; font-variant-numeric: tabular-nums; }
.ot-kpi .d .up { color: #198038; font-weight: 600; }
.ot-kpi .d .down { color: #da1e28; font-weight: 600; }
.ot-kpi svg { flex: none; }

/* notas bajo las graficas */
[class*="st-key-nota-"] { border-left: 2px solid #8d8d8d; padding: .1rem 0 .1rem .75rem !important; gap: 0; }
[class*="st-key-nota-observado"] { border-left-color: #0f62fe; }
[class*="st-key-nota-estimacion"] { border-left-color: #8a3ffc; }
[class*="st-key-nota-"] p { font-size: .8125rem; color: #393939; line-height: 1.5; margin-bottom: .2rem; }
.ot-nl { font-size: .6875rem; color: #6f6f6f; margin-bottom: .1rem; }

/* accesos de la portada */
[class*="st-key-acceso-"] { background: #ffffff; border: 1px solid #e0e0e0; padding: 1rem !important; min-height: 10.5rem; justify-content: space-between; }
.ot-acc-t { font-size: 1rem; font-weight: 600; color: #161616; }
.ot-acc-d { font-size: .8125rem; color: #525252; line-height: 1.5; margin-top: .3rem; }

[data-testid="stCaptionContainer"] { color: #6f6f6f; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { font-size: .7rem; line-height: 1.45; }
</style>
"""


def _clave(*partes: object) -> str:
    """Clave estable entre ejecuciones para contenedores con estilo propio."""
    return f"{crc32('|'.join(map(str, partes)).encode()):x}"


def estilo_global() -> None:
    st.html(_CSS)


def encabezado_pagina(seccion: str, titulo: str, descripcion: str | None = None, meta: str | None = None) -> None:
    desc = f'<p class="ot-desc">{descripcion}</p>' if descripcion else ""
    der = f'<div class="ot-meta">{meta}</div>' if meta else ""
    st.html(
        f'<div class="ot-head"><div><div class="ot-crumb">{html.escape(seccion)}</div>'
        f'<h1 class="ot-h1">{html.escape(titulo)}</h1>{desc}</div>{der}</div>'
    )


def _tag(tipo: str) -> str:
    texto, color, fondo = TIPO_INFO[tipo]
    return f'<span class="ot-tag" style="color:{color};background:{fondo}">{texto}</span>'


@contextmanager
def mosaico(clave: str, titulo: str, subtitulo: str, tipo: str, ayuda: str, filtro: str | None = None):
    """Mosaico de una visualizacion: titulo, subtitulo con unidades y alcance, etiqueta de
    tipo de dato, chip del filtro cruzado activo y la explicacion en un icono de informacion."""
    with st.container(key=f"tile-{clave}"):
        izq, der, info = st.columns([0.62, 0.32, 0.06], vertical_alignment="top", gap="small")
        izq.html(f'<div class="ot-tt">{html.escape(titulo)}</div><div class="ot-ts">{subtitulo}</div>')
        chip = f'<span class="ot-chip" title="{html.escape(filtro)}">Filtrado por: {html.escape(filtro)}</span>' if filtro else ""
        der.html(f'<div class="ot-tags">{chip}{_tag(tipo)}</div>')
        with info.popover("", icon=":material/info:", help="Acerca de esta gráfica"):
            st.markdown(ayuda)
        yield


def _sparkline(valores: list[float], ancho: int = 96, alto: int = 30) -> str:
    v = [float(x) for x in valores if pd.notna(x)]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    rango = hi - lo or 1.0
    pts = [(i * (ancho - 4) / (len(v) - 1) + 2, alto - 3 - (y - lo) / rango * (alto - 6)) for i, y in enumerate(v)]
    camino = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    x, y = pts[-1]
    return (
        f'<svg width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" aria-hidden="true">'
        f'<polyline points="{camino}" fill="none" stroke="#8d8d8d" stroke-width="1.25"/>'
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="#161616"/></svg>'
    )


def indicadores(items: list[dict]) -> None:
    """Fila de indicadores. Cada item: etiqueta, valor y, opcionalmente, delta (fraccion) con
    delta_texto, o contexto; y serie para la minigrafica."""
    celdas = []
    for it in items:
        if it.get("delta") is not None:
            d = it["delta"]
            clase, flecha = ("up", "▲") if d >= 0 else ("down", "▼")
            pie = f'<span class="{clase}">{flecha} {abs(d):.0%}</span> {html.escape(it.get("delta_texto", ""))}'
        else:
            pie = html.escape(it.get("contexto", ""))
        celdas.append(
            f'<div class="ot-kpi"><div class="l">{html.escape(it["etiqueta"])}</div>'
            f'<div class="row"><div class="v">{html.escape(it["valor"])}</div>{_sparkline(it.get("serie", []))}</div>'
            f'<div class="d">{pie}</div></div>'
        )
    st.html(f'<div class="ot-kpis">{"".join(celdas)}</div>')


def nota(tipo: str, texto: str) -> None:
    """Lectura breve bajo una grafica, marcada como observado, interpretacion o estimacion."""
    with st.container(key=f"nota-{tipo}-{_clave(texto)}"):
        st.html(f'<div class="ot-nl">{TIPO_INFO[tipo][0]}</div>')
        st.markdown(texto)


@contextmanager
def barra_filtros(nombre: str):
    with st.container(key=f"filtros-{nombre}"):
        yield


def personalizar_vista(opciones: dict[str, str], key: str) -> set[str]:
    """Menu para elegir que graficas de la pagina se muestran."""
    with st.popover("Personalizar vista", icon=":material/tune:", width="stretch"):
        elegidas = st.pills(
            "Gráficas visibles", list(opciones), format_func=lambda k: opciones[k],
            selection_mode="multi", default=list(opciones), key=key,
        )
    return set(elegidas or [])


def encabezado_con_vista(seccion: str, titulo: str, descripcion: str | None, meta: str, opciones: dict[str, str], key: str) -> set[str]:
    """Encabezado de pagina con el menu de vista a la derecha."""
    izq, der = st.columns([0.82, 0.18], vertical_alignment="bottom")
    with izq:
        encabezado_pagina(seccion, titulo, descripcion)
    with der:
        st.html(f'<div class="ot-meta" style="margin-bottom:.4rem">{meta}</div>')
        visibles = personalizar_vista(opciones, key)
    if not visibles:
        st.info("Todas las gráficas están ocultas. Actívelas desde **Personalizar vista**.", icon=":material/visibility_off:")
    return visibles


def filtros_viajeros(df: pd.DataFrame, key: str, extra: int = 0) -> tuple[tuple[int, int], list[str], list[str], list]:
    """Filtros comunes (anios, tipo de viajero, via) y `extra` columnas libres en la misma fila."""
    anio_min, anio_max = int(df["anio"].min()), int(df["anio"].max())
    cols = st.columns([1.0, 1.35, 1.6] + [1.25] * extra, gap="medium")
    anios = cols[0].slider("Años", anio_min, anio_max, (anio_min, anio_max), key=f"{key}_anios")
    tipos_disp = sorted(df["tipo"].unique())
    tipos = cols[1].multiselect(
        "Tipo de viajero", tipos_disp, default=[t for t in TIPOS_COMPARABLES if t in tipos_disp], key=f"{key}_tipos",
        help="Turistas y excursionistas son los únicos tipos registrados de la misma forma en todo 2009-2026.",
    )
    vias = cols[2].multiselect("Vía de ingreso", ORDEN_VIA, default=ORDEN_VIA, key=f"{key}_vias")
    return anios, tipos, vias, cols[3:]


def sin_datos(mensaje: str) -> None:
    st.warning(mensaje, icon=":material/search_off:")


def meta_datos(df: pd.DataFrame) -> str:
    ultimo = df["fecha"].max()
    return f"Datos hasta <b>{MESES_CORTOS[ultimo.month - 1]} {ultimo.year}</b><br>Fuente: base de migración"
