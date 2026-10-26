"""Mercados y recuperacion: indice anual por categoria (grafica 5) enlazado con el arbol region -> pais (grafica 6)."""

from __future__ import annotations

import streamlit as st

from src.datos import cargar_viajeros, filtrar
from src.estilo import formato_numero
from src.graficas import figura_recuperacion, figura_treemap, indice_recuperacion
from src.ui import barra_filtros, encabezado_pagina, filtros_viajeros, hallazgo, selector_graficas, sin_datos, tarjeta_grafica

DIMENSIONES_INDICE = {
    "Región de origen": "region",
    "Vía de ingreso": "via",
    "Frontera / puesto de ingreso": "frontera",
}

encabezado_pagina(
    "Explorar los datos · 3 de 3",
    "Mercados y recuperación",
    "Qué mercados y puestos de ingreso ya superaron su nivel previo a la pandemia y cuáles siguen por debajo. "
    "Al hacer clic en una celda del índice, el árbol de abajo muestra de qué países vinieron esos viajeros.",
)

df = cargar_viajeros()
with barra_filtros("mercados"):
    anios, tipos, vias, _ = filtros_viajeros(df, "merc")
    visibles = selector_graficas({"indice": "5 · Índice de recuperación", "arbol": "6 · Árbol de orígenes"}, key="merc_vis")

datos = filtrar(df, anios, tipos, vias)
if datos.empty or datos["viajeros"].sum() == 0:
    sin_datos("No hay viajeros para esta combinación de filtros. Amplíe el rango de años o agregue tipos de viajero y vías.")
    st.stop()

seleccion: tuple[str, int] | None = None
dimension = "region"
if "indice" in visibles:
    with tarjeta_grafica(
        5,
        "¿Cuánto se recuperó cada mercado?",
        "observado",
        "Sirve para ver qué mercados o puestos ya se recuperaron y cuáles necesitan una estrategia de reactivación.",
        "Cada celda compara un año con el año base: **100** significa el mismo volumen, **150** un 50 % más y "
        "**50** la mitad. El azul indica que se está por encima del año base; el rojo, por debajo; el gris, un nivel "
        "similar. Cada año se compara con los mismos meses del año base, para que un año incompleto como 2026 no "
        "parezca una caída.\n\n"
        "**Para profundizar:** haga clic en una celda y la gráfica 6 mostrará los países de origen de esa "
        "categoría en ese año.",
        "<b>Clic en una celda</b> para ver sus países de origen en la gráfica 6",
    ):
        c1, c2, c3 = st.columns(3)
        dim_label = c1.selectbox("Comparar por", list(DIMENSIONES_INDICE), key="merc_dim")
        dimension = DIMENSIONES_INDICE[dim_label]
        anios_disp = sorted(datos["anio"].unique())
        base = c2.selectbox(
            "Año base (= 100)", anios_disp, index=anios_disp.index(2019) if 2019 in anios_disp else 0, key="merc_base",
            help="2019 es el último año completo antes de la pandemia.",
        )
        top_n = c3.slider("Cantidad de filas", 3, 15, 8, key="merc_top", help="Más filas incluyen categorías con menos viajeros.")
        indice = indice_recuperacion(datos, dimension, int(base), top_n)
        if indice.empty or indice.isna().all().all():
            sin_datos(f"Ninguna categoría filtrada tuvo viajeros en {base}, así que no se puede calcular el índice. Elija otro año base.")
        else:
            evento = st.plotly_chart(
                figura_recuperacion(indice, int(base)), key=f"indice_{dimension}_{base}", on_select="rerun",
                selection_mode="points", width="stretch",
            )
            puntos = evento.selection.points if evento and evento.selection else []
            if puntos and "y" in puntos[0] and "x" in puntos[0]:
                seleccion = (str(puntos[0]["y"]), int(puntos[0]["x"]))
            st.caption(
                "Las celdas vacías corresponden a categorías sin viajeros en el año base."
                + (" Desde 2023 la fuente agrupa algunos países en mercados, lo que también puede mover el índice por región." if dimension == "region" else "")
            )

if "arbol" in visibles:
    if seleccion:
        cat, anio_sel = seleccion
        detalle = datos[(datos[dimension].astype(str) == cat) & (datos["anio"] == anio_sel)]
        titulo = f"{cat}, {anio_sel}"
    else:
        detalle = datos
        titulo = f"{anios[0]}-{anios[1]}"
    with tarjeta_grafica(
        6,
        f"¿De qué regiones y países vienen? · {titulo}",
        "observado",
        "Sirve para medir el peso de cada mercado y decidir dónde concentrar la promoción.",
        "Cada rectángulo es una región de origen y, dentro de ella, sus países. El tamaño y el tono indican cuántos "
        "viajeros aportó cada uno.\n\n"
        "**Para profundizar:** haga clic en una región para acercarse y en la barra superior para volver.",
        "<b>Clic en una región</b> para acercarse · barra superior para volver",
    ):
        profundidad = st.segmented_control(
            "Nivel de detalle", ["Regiones", "Regiones y países"], default="Regiones y países", key="merc_prof"
        ) or "Regiones y países"
        if detalle.empty or detalle["viajeros"].sum() == 0:
            sin_datos("La selección no tiene viajeros registrados. Elija otra celda o restablezca la selección con doble clic.")
        else:
            st.plotly_chart(figura_treemap(detalle, 1 if profundidad == "Regiones" else 2), key="arbol", width="stretch")
            por_region = detalle.groupby("region", observed=True)["viajeros"].sum().sort_values(ascending=False)
            por_region = por_region[por_region > 0]
            top_pais = detalle.groupby("pais", observed=True)["viajeros"].sum().nlargest(3)
            c1, c2 = st.columns(2)
            with c1:
                hallazgo(
                    "observado",
                    f"**{por_region.index[0]}** aporta el {por_region.iloc[0] / por_region.sum():.0%} de los viajeros "
                    f"({formato_numero(por_region.iloc[0])} de {formato_numero(por_region.sum())}). Los tres países principales son "
                    + ", ".join(f"{p} ({formato_numero(v)})" for p, v in top_pais.items()) + ".",
                )
            with c2:
                hallazgo(
                    "interpretacion",
                    "Depender de pocos mercados facilita enfocar la promoción, pero deja al destino expuesto a lo que "
                    "ocurra en ellos. Los datos muestran cuánto pesa cada mercado, no por qué crece o cae.",
                )
