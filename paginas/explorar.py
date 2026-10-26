"""Evolucion y origen: grafica 1 (llegadas por via) filtra a la grafica 2 (origen de la seleccion)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.datos import DIMENSIONES, NIVELES_TIEMPO, agregar_periodo, cargar_viajeros, filtrar
from src.estilo import ORDEN_VIA, formato_numero
from src.graficas import figura_evolucion, figura_origen
from src.ui import barra_filtros, encabezado_con_vista, filtros_viajeros, indicadores, meta_datos, mosaico, sin_datos

df = cargar_viajeros()
ultimo_mes = df["fecha"].max()

visibles = encabezado_con_vista(
    "Explorar · Demanda",
    "Evolución y origen",
    None,
    meta_datos(df),
    {"evolucion": "Llegadas por vía", "origen": "Origen de los viajeros"},
    "explorar_vis",
)

with barra_filtros("explorar"):
    anios, tipos, vias, (c_nivel,) = filtros_viajeros(df, "expl", extra=1)
    nivel = c_nivel.segmented_control("Detalle temporal", NIVELES_TIEMPO, default="Año", key="expl_nivel") or "Año"

datos = filtrar(df, anios, tipos, vias)
if datos.empty or datos["viajeros"].sum() == 0:
    sin_datos("No hay viajeros para esta combinación de filtros. Amplíe el rango de años o agregue tipos de viajero y vías.")
    st.stop()

# Indicadores
por_anio = datos.groupby("anio")["viajeros"].sum()
meses_anio = datos.groupby("anio")["mes"].nunique()
completos = list(meses_anio[meses_anio == 12].index)
total = datos["viajeros"].sum()
por_via = datos.groupby("via", observed=True)["viajeros"].sum()
kpis = [
    {"etiqueta": f"Viajeros {anios[0]}–{anios[1]}", "valor": formato_numero(total),
     "contexto": f"{datos['fecha'].nunique()} meses con registro", "serie": por_anio.tolist()},
]
if len(completos) >= 2:
    a, b = completos[-1], completos[-2]
    kpis.append({"etiqueta": f"Viajeros {a}", "valor": formato_numero(por_anio[a]), "delta": por_anio[a] / por_anio[b] - 1, "delta_texto": f"frente a {b}"})
kpis.append({"etiqueta": "Vía principal", "valor": por_via.idxmax(), "contexto": f"{por_via.max() / total:.0%} de las llegadas del periodo"})
indicadores(kpis)

datos = datos.assign(periodo=agregar_periodo(datos["fecha"], nivel))
unidad = {"Año": "año", "Trimestre": "trimestre", "Mes": "mes"}[nivel]

if {"evolucion", "origen"} <= visibles:
    col_a, col_b = st.columns([1.35, 1], gap="small")
else:
    col_a = col_b = st.container()

evento, vias_trazas = None, []
if "evolucion" in visibles:
    with col_a, mosaico(
        "evolucion",
        "Llegadas por vía de ingreso",
        f"Viajeros por {unidad} · seleccione barras para filtrar el origen",
        "observado",
        "**¿Cómo ha evolucionado la llegada de viajeros y por qué vía entran?**\n\n"
        "Cada barra suma los viajeros del periodo y cada color es una vía. Al hacer clic en un segmento, la gráfica "
        "de origen muestra solo esos viajeros. Shift + clic suma segmentos, la herramienta de caja elige un rango y "
        "el doble clic restablece la selección.",
    ):
        fig1, vias_trazas = figura_evolucion(datos, nivel)
        evento = st.plotly_chart(fig1, key=f"evolucion_{nivel}", on_select="rerun", selection_mode=("points", "box"), width="stretch")
        if ultimo_mes.month < 12 and anios[1] == ultimo_mes.year:
            st.caption(f"{ultimo_mes.year} incluye datos hasta {ultimo_mes:%m/%Y}.")

puntos = evento.selection.points if evento and evento.selection else []
seleccion = {(p["x"], vias_trazas[p["curve_number"]]) for p in puntos if "x" in p and "curve_number" in p}
filtro = None
if seleccion:
    sel_df = pd.DataFrame(list(seleccion), columns=["periodo", "via"])
    detalle = datos.merge(sel_df, on=["periodo", "via"])
    sel_periodos = sorted(sel_df["periodo"].unique())
    sel_vias = [v for v in ORDEN_VIA if v in set(sel_df["via"])]
    texto_periodo = ", ".join(sel_periodos) if len(sel_periodos) <= 3 else f"{sel_periodos[0]} a {sel_periodos[-1]}"
    filtro = f"{texto_periodo} · {', '.join(sel_vias)}"
else:
    detalle = datos

if "origen" in visibles:
    with col_b, mosaico(
        "origen",
        "Origen de los viajeros",
        "Viajeros por categoría, de mayor a menor",
        "observado",
        "**¿De dónde vienen los viajeros y por qué puestos entran?**\n\n"
        "Muestra las categorías con más viajeros dentro de lo seleccionado en la gráfica de evolución, divididas por "
        "vía. Se puede cambiar la dimensión y la cantidad de categorías. Desde 2023 la fuente agrupa algunos países "
        "en mercados; las comparaciones por país que cruzan ese año deben tomarse con cautela.",
        filtro=filtro,
    ):
        d1, d2 = st.columns(2)
        dim_label = d1.selectbox("Dimensión", list(DIMENSIONES), key="expl_dim")
        top_n = d2.slider("Categorías", 5, 25, 10, key="expl_top")
        dimension = DIMENSIONES[dim_label]
        if detalle.empty or detalle["viajeros"].sum() == 0:
            sin_datos("La selección no tiene viajeros registrados. Elija otra barra o restablezca con doble clic.")
        else:
            fig2, totales, desglose = figura_origen(detalle, dimension, top_n)
            top = totales.head(top_n)
            st.plotly_chart(fig2, key="detalle", width="stretch")
            st.caption(f"Las {len(top)} categorías reúnen el {top.sum() / totales.sum():.0%} de los viajeros ({formato_numero(top.sum())}).")
            with st.expander("Tabla", icon=":material/table:"):
                tabla = (
                    desglose.pivot_table(index=dimension, columns="via", values="viajeros", aggfunc="sum", fill_value=0, observed=True)
                    .reindex(columns=[v for v in ORDEN_VIA if v in set(desglose["via"])])
                    .assign(Total=lambda t: t.sum(axis=1))
                    .sort_values("Total", ascending=False)
                )
                tabla.index.name = dim_label
                st.dataframe(tabla.style.format("{:,.0f}"), width="stretch")
