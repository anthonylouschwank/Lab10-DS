"""Explorar llegadas: dos visualizaciones enlazadas.

1. Evolucion de llegadas por via (barras apiladas). Al hacer clic o arrastrar sobre
   las barras se seleccionan periodos y vias.
2. Origen / puesto de ingreso de la seleccion (barras horizontales apiladas por via).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.datos import DIMENSIONES, NIVELES_TIEMPO, TIPOS_COMPARABLES, agregar_periodo, cargar_viajeros, filtrar
from src.estilo import ORDEN_VIA, formato_numero
from src.graficas import figura_evolucion, figura_origen

st.title("Explorar llegadas de viajeros")
st.caption(
    "Viajeros internacionales que ingresaron a Guatemala por mes. "
    "Datos de uso académico; no son cifras oficiales."
)

df = cargar_viajeros()
anio_min, anio_max = int(df["anio"].min()), int(df["anio"].max())
ultimo_mes = df["fecha"].max()

# ---------------------------------------------------------------- filtros
c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
anios = c1.slider("Años", anio_min, anio_max, (anio_min, anio_max))
tipos = c2.multiselect(
    "Tipo de viajero",
    sorted(df["tipo"].unique()),
    default=[t for t in TIPOS_COMPARABLES if t in set(df["tipo"].unique())],
    help="Por defecto solo turistas y excursionistas: son los únicos tipos registrados de forma comparable en todo 2009-2026.",
)
vias = c3.multiselect("Vía de ingreso", ORDEN_VIA, default=ORDEN_VIA)
nivel = c4.segmented_control(
    "Detalle temporal",
    NIVELES_TIEMPO,
    default="Año",
    help="Aumenta o disminuye el nivel de detalle de la gráfica de evolución.",
) or "Año"

datos = filtrar(df, anios, tipos, vias)
if datos.empty:
    st.warning("No hay viajeros para la combinación de filtros elegida. Amplía el rango de años o agrega tipos de viajero y vías.")
    st.stop()

# ---------------------------------------------------------------- resumen (no cuenta como visualizacion)
total = datos["viajeros"].sum()
por_via = datos.groupby("via", observed=True)["viajeros"].sum()
via_principal = por_via.idxmax()
k1, k2, k3 = st.columns(3)
k1.metric("Viajeros en el periodo", formato_numero(total))
k2.metric(f"Vía principal ({por_via.max() / total:.0%} del total)", via_principal)
k3.metric("Meses incluidos", f"{datos['fecha'].nunique()}")

# ---------------------------------------------------------------- viz 1: evolucion
st.subheader("1. ¿Cómo ha evolucionado la llegada de viajeros?")
st.caption(
    "Cada barra suma los viajeros del periodo, dividida por vía de ingreso. "
    "**Haz clic en una barra** para ver abajo de dónde vinieron esos viajeros. "
    "Mantén Shift para sumar varias barras, o usa la herramienta de caja (arriba a la derecha) para elegir un rango. "
    "Doble clic sobre la gráfica limpia la selección."
)

datos = datos.assign(periodo=agregar_periodo(datos["fecha"], nivel))
fig1, vias_trazas = figura_evolucion(datos, nivel)

evento = st.plotly_chart(
    fig1,
    key=f"evolucion_{nivel}",
    on_select="rerun",
    selection_mode=("points", "box"),
    use_container_width=True,
)
if ultimo_mes.month < 12 and anios[1] == ultimo_mes.year:
    st.caption(f"{ultimo_mes.year} solo incluye datos hasta {ultimo_mes:%m/%Y}; su barra anual no está completa.")

# Parejas (periodo, via) seleccionadas en la grafica 1
puntos = evento.selection.points if evento and evento.selection else []
seleccion = {(p["x"], vias_trazas[p["curve_number"]]) for p in puntos if "x" in p and "curve_number" in p}

if seleccion:
    sel_df = pd.DataFrame(list(seleccion), columns=["periodo", "via"])
    detalle = datos.merge(sel_df, on=["periodo", "via"])
    sel_periodos = sorted(sel_df["periodo"].unique())
    sel_vias = [v for v in ORDEN_VIA if v in set(sel_df["via"])]
    texto_periodo = ", ".join(sel_periodos) if len(sel_periodos) <= 4 else f"{len(sel_periodos)} periodos ({sel_periodos[0]} a {sel_periodos[-1]})"
    texto_seleccion = f"{texto_periodo} · vía {', '.join(sel_vias)}"
else:
    detalle = datos
    texto_seleccion = f"todo el periodo filtrado ({anios[0]}-{anios[1]})"

# ---------------------------------------------------------------- viz 2: detalle de la seleccion
st.subheader("2. ¿De dónde vienen y por dónde entran?")
d1, d2 = st.columns([2, 2])
dim_label = d1.selectbox("Ver por", list(DIMENSIONES), help="Cambia la categoría con la que se desglosa la selección.")
top_n = d2.slider("Cantidad de categorías", 5, 25, 10, help="Más categorías = más detalle.")
dimension = DIMENSIONES[dim_label]

st.caption(f"Mostrando: **{texto_seleccion}**" + ("" if seleccion else " — selecciona barras arriba para enfocarte en un periodo o vía."))

if detalle.empty or detalle["viajeros"].sum() == 0:
    st.info("La selección no tiene viajeros registrados. Elige otra barra o limpia la selección con doble clic.")
    st.stop()

fig2, totales, desglose = figura_origen(detalle, dimension, top_n)
top = totales.head(top_n)
cobertura = top.sum() / totales.sum()

st.plotly_chart(fig2, key="detalle", use_container_width=True)
st.caption(
    f"Las {len(top)} categorías mostradas suman el {cobertura:.0%} de los viajeros de la selección "
    f"({formato_numero(top.sum())} de {formato_numero(totales.sum())})."
)
if dimension == "pais" and anios[1] >= 2023:
    st.caption(
        "Nota: desde 2023 la fuente agrupa algunos países en mercados (por ejemplo, regiones), "
        "por lo que la comparación por país antes y después de 2023 debe tomarse con cautela."
    )

with st.expander("Ver datos de la selección en tabla"):
    tabla = (
        desglose.pivot_table(index=dimension, columns="via", values="viajeros", aggfunc="sum", fill_value=0, observed=True)
        .reindex(columns=[v for v in ORDEN_VIA if v in set(desglose["via"])])
        .assign(Total=lambda t: t.sum(axis=1))
        .sort_values("Total", ascending=False)
    )
    tabla.index.name = dim_label
    st.dataframe(tabla.style.format("{:,.0f}"), use_container_width=True)
