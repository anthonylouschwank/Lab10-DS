"""Mercados y recuperacion: indice anual por categoria (viz 5) enlazado con el arbol region -> pais (viz 6)."""

from __future__ import annotations

import streamlit as st

from src.datos import cargar_viajeros, filtrar
from src.estilo import formato_numero
from src.graficas import figura_recuperacion, figura_treemap, indice_recuperacion
from src.ui import encabezado_grafica, etiqueta, filtros_viajeros, nota_fuente, selector_graficas, sin_datos

DIMENSIONES_INDICE = {
    "Región de origen": "region",
    "Vía de ingreso": "via",
    "Frontera / puesto de ingreso": "frontera",
}

st.title("Mercados y recuperación")
st.markdown(
    "¿Qué mercados y puestos de ingreso ya superaron su nivel previo a la pandemia y cuáles siguen por debajo? "
    "Haz clic en una celda del índice para ver, en el árbol de abajo, de qué países vinieron esos viajeros ese año."
)
nota_fuente()

df = cargar_viajeros()
anios, tipos, vias = filtros_viajeros(df, key="merc")
datos = filtrar(df, anios, tipos, vias)
if datos.empty or datos["viajeros"].sum() == 0:
    sin_datos("No hay viajeros para la combinación de filtros elegida. Amplía el rango de años o agrega tipos de viajero y vías.")
    st.stop()

visibles = selector_graficas({"indice": "5. Índice de recuperación", "arbol": "6. Árbol de orígenes"}, key="merc_vis")

c1, c2, c3 = st.columns(3)
dim_label = c1.selectbox("Comparar por", list(DIMENSIONES_INDICE), key="merc_dim")
dimension = DIMENSIONES_INDICE[dim_label]
anios_disp = sorted(datos["anio"].unique())
base = c2.selectbox(
    "Año base (= 100)",
    anios_disp,
    index=anios_disp.index(2019) if 2019 in anios_disp else 0,
    key="merc_base",
    help="2019 es el último año completo antes de la pandemia.",
)
top_n = c3.slider("Cantidad de filas", 3, 15, 8, key="merc_top", help="Más filas = más detalle (categorías con menos viajeros).")

seleccion: tuple[str, int] | None = None
if "indice" in visibles:
    encabezado_grafica(
        5,
        f"¿Cuánto se recuperó cada {dim_label.lower().split(' /')[0]} respecto a {base}?",
        "observado",
        f"un índice por año: 100 = mismo volumen que en {base}; 150 = 50 % más; 50 = la mitad. "
        "**Azul** = por encima del año base, **rojo** = por debajo, gris = similar. Cada año se compara con los mismos meses del año base.",
        "ver qué mercados o puestos ya se recuperaron y cuáles requieren atención o estrategias de reactivación.",
    )
    indice = indice_recuperacion(datos, dimension, int(base), top_n)
    if indice.empty or indice.isna().all().all():
        sin_datos(f"No hay viajeros en {base} para las categorías filtradas, así que no se puede calcular el índice. Elige otro año base.")
    else:
        st.caption("**Haz clic en una celda** para ver el detalle de esa categoría y año en la gráfica 6. Doble clic limpia la selección.")
        evento = st.plotly_chart(
            figura_recuperacion(indice, int(base)), key=f"indice_{dimension}_{base}", on_select="rerun",
            selection_mode="points", use_container_width=True,
        )
        puntos = evento.selection.points if evento and evento.selection else []
        if puntos and "y" in puntos[0] and "x" in puntos[0]:
            seleccion = (str(puntos[0]["y"]), int(puntos[0]["x"]))
        st.caption(
            "Celdas vacías: la categoría no registró viajeros en el año base. "
            + ("Desde 2023 algunos países se agrupan en mercados; los cambios por región pueden reflejar parcialmente ese cambio de registro." if dimension == "region" else "")
        )

if "arbol" in visibles:
    if seleccion:
        cat, anio_sel = seleccion
        detalle = datos[(datos[dimension].astype(str) == cat) & (datos["anio"] == anio_sel)]
        titulo = f"{cat} · {anio_sel}"
    else:
        detalle = datos
        titulo = f"todo el periodo filtrado ({anios[0]}-{anios[1]})"
    encabezado_grafica(
        6,
        f"¿De qué regiones y países vienen? — {titulo}",
        "observado",
        "cada rectángulo es una región de origen y, dentro, sus países; el tamaño y el tono indican cuántos viajeros aportaron.",
        "dimensionar el peso de cada mercado para priorizar promoción. **Haz clic en una región** para acercarte; "
        "clic en la barra superior para volver.",
    )
    profundidad = st.segmented_control(
        "Nivel de detalle", ["Regiones", "Regiones y países"], default="Regiones y países", key="merc_prof"
    ) or "Regiones y países"
    if detalle.empty or detalle["viajeros"].sum() == 0:
        sin_datos("La selección no tiene viajeros registrados. Elige otra celda o limpia la selección con doble clic.")
    else:
        st.plotly_chart(
            figura_treemap(detalle, 1 if profundidad == "Regiones" else 2), key="arbol", use_container_width=True
        )
        por_region = detalle.groupby("region", observed=True)["viajeros"].sum().sort_values(ascending=False)
        por_region = por_region[por_region > 0]
        top_pais = detalle.groupby("pais", observed=True)["viajeros"].sum().nlargest(3)
        etiqueta("observado")
        st.markdown(
            f"- **{por_region.index[0]}** aporta el {por_region.iloc[0] / por_region.sum():.0%} de los viajeros de la selección "
            f"({formato_numero(por_region.iloc[0])} de {formato_numero(por_region.sum())}).\n"
            f"- Principales países: {', '.join(f'{p} ({formato_numero(v)})' for p, v in top_pais.items())}."
        )
        etiqueta("interpretacion")
        st.markdown(
            "Una concentración alta en pocos mercados simplifica la promoción, pero también expone al destino a lo que "
            "ocurra en esos mercados. Estos datos no indican por qué un mercado crece o cae."
        )
