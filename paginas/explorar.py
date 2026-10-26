"""Evolucion y origen: grafica 1 (evolucion por via) enlazada con la grafica 2 (origen de la seleccion)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.datos import DIMENSIONES, NIVELES_TIEMPO, agregar_periodo, cargar_viajeros, filtrar
from src.estilo import ORDEN_VIA, formato_numero
from src.graficas import figura_evolucion, figura_origen
from src.ui import barra_filtros, encabezado_pagina, filtros_viajeros, indicadores, selector_graficas, sin_datos, tarjeta_grafica

encabezado_pagina(
    "Explorar los datos · 1 de 3",
    "Evolución y origen de los viajeros",
    "Cuántos viajeros internacionales llegan, por qué vía y desde dónde. Al seleccionar barras en la "
    "primera gráfica, la segunda muestra el origen de esos viajeros.",
)

df = cargar_viajeros()
ultimo_mes = df["fecha"].max()

with barra_filtros("explorar"):
    anios, tipos, vias, (c_nivel,) = filtros_viajeros(df, "expl", extra=1)
    nivel = c_nivel.segmented_control(
        "Detalle temporal", NIVELES_TIEMPO, default="Año", key="expl_nivel",
        help="Más o menos detalle en la gráfica 1: años, trimestres o meses.",
    ) or "Año"
    visibles = selector_graficas({"evolucion": "1 · Evolución por vía", "origen": "2 · Origen y puesto de ingreso"}, key="explorar_vis")

datos = filtrar(df, anios, tipos, vias)
if datos.empty or datos["viajeros"].sum() == 0:
    sin_datos("No hay viajeros para esta combinación de filtros. Amplíe el rango de años o agregue tipos de viajero y vías.")
    st.stop()

total = datos["viajeros"].sum()
por_via = datos.groupby("via", observed=True)["viajeros"].sum()
indicadores(
    [
        ("Viajeros en el periodo", formato_numero(total), f"{anios[0]}-{anios[1]} · {', '.join(t.lower() for t in tipos)}"),
        ("Vía principal", por_via.idxmax(), f"{por_via.max() / total:.0%} de las llegadas"),
        ("Meses con registro", f"{datos['fecha'].nunique()}", f"hasta {ultimo_mes:%m/%Y}"),
    ]
)

datos = datos.assign(periodo=agregar_periodo(datos["fecha"], nivel))
evento, vias_trazas = None, []
if "evolucion" in visibles:
    with tarjeta_grafica(
        1,
        "¿Cómo ha evolucionado la llegada de viajeros?",
        "observado",
        "Sirve para dimensionar la demanda, ubicar la caída de 2020 y seguir la recuperación de cada vía.",
        "Cada barra es un periodo; su altura, el total de viajeros, y cada color, una vía de ingreso. "
        "El control **Detalle temporal** cambia entre años, trimestres y meses.\n\n"
        "**Para profundizar:** haga clic en un segmento y la gráfica 2 mostrará el origen de esos viajeros. "
        "Con Shift puede sumar varios segmentos; con la herramienta de caja (esquina superior derecha), un rango. "
        "Doble clic restablece la selección.",
        "<b>Clic en una barra</b> para ver su origen en la gráfica 2 · doble clic para restablecer",
    ):
        fig1, vias_trazas = figura_evolucion(datos, nivel)
        evento = st.plotly_chart(fig1, key=f"evolucion_{nivel}", on_select="rerun", selection_mode=("points", "box"), width="stretch")
        if ultimo_mes.month < 12 and anios[1] == ultimo_mes.year:
            st.caption(f"{ultimo_mes.year} solo tiene datos hasta {ultimo_mes:%m/%Y}: su barra anual está incompleta.")

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

if "origen" in visibles:
    with tarjeta_grafica(
        2,
        "¿De dónde vienen y por dónde entran?",
        "observado",
        "Sirve para saber qué mercados y qué puestos fronterizos concentran la demanda.",
        "Muestra las categorías con más viajeros dentro de lo seleccionado en la gráfica 1, ordenadas de mayor a menor "
        "y divididas por vía. Puede ver la selección por región, país, puesto de ingreso o región de la OMT, "
        "y elegir cuántas categorías mostrar (más categorías, más detalle).",
    ):
        d1, d2 = st.columns(2)
        dim_label = d1.selectbox("Ver por", list(DIMENSIONES), key="expl_dim")
        top_n = d2.slider("Cantidad de categorías", 5, 25, 10, key="expl_top")
        dimension = DIMENSIONES[dim_label]
        st.caption(f"Mostrando: **{texto_seleccion}**" + ("" if seleccion else ". Seleccione barras en la gráfica 1 para enfocarse en un periodo o una vía."))

        if detalle.empty or detalle["viajeros"].sum() == 0:
            sin_datos("La selección no tiene viajeros registrados. Elija otra barra o restablezca la selección con doble clic.")
        else:
            fig2, totales, desglose = figura_origen(detalle, dimension, top_n)
            top = totales.head(top_n)
            st.plotly_chart(fig2, key="detalle", width="stretch")
            st.caption(
                f"Las {len(top)} categorías mostradas reúnen el {top.sum() / totales.sum():.0%} de los viajeros de la selección "
                f"({formato_numero(top.sum())} de {formato_numero(totales.sum())})."
                + (" Desde 2023 la fuente agrupa algunos países en mercados; compare por país antes y después de ese año con cautela."
                   if dimension == "pais" and anios[1] >= 2023 else "")
            )
            with st.expander("Ver la tabla completa", icon=":material/table:"):
                tabla = (
                    desglose.pivot_table(index=dimension, columns="via", values="viajeros", aggfunc="sum", fill_value=0, observed=True)
                    .reindex(columns=[v for v in ORDEN_VIA if v in set(desglose["via"])])
                    .assign(Total=lambda t: t.sum(axis=1))
                    .sort_values("Total", ascending=False)
                )
                tabla.index.name = dim_label
                st.dataframe(tabla.style.format("{:,.0f}"), width="stretch")
