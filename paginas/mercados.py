"""Mercados y recuperacion: indice anual por categoria (grafica 5) filtra el arbol region -> pais (grafica 6)."""

from __future__ import annotations

import streamlit as st

from src.datos import cargar_viajeros, filtrar
from src.estilo import formato_numero
from src.graficas import figura_recuperacion, figura_treemap, indice_recuperacion
from src.ui import barra_filtros, encabezado_con_vista, filtros_viajeros, indicadores, meta_datos, mosaico, nota, sin_datos

DIMENSIONES_INDICE = {"Región de origen": "region", "Vía de ingreso": "via", "Frontera / puesto de ingreso": "frontera"}
NOMBRE_CORTO = {"América Del Centro": "Centroamérica", "América Del Norte": "Norteamérica", "América Del Sur y el Caribe": "Sudamérica y el Caribe"}

df = cargar_viajeros()
visibles = encabezado_con_vista(
    "Explorar · Mercados",
    "Mercados y recuperación",
    None,
    meta_datos(df),
    {"indice": "Índice de recuperación", "arbol": "Orígenes por región y país"},
    "merc_vis",
)

with barra_filtros("mercados"):
    anios, tipos, vias, _ = filtros_viajeros(df, "merc")

datos = filtrar(df, anios, tipos, vias)
if datos.empty or datos["viajeros"].sum() == 0:
    sin_datos("No hay viajeros para esta combinación de filtros. Amplíe el rango de años o agregue tipos de viajero y vías.")
    st.stop()

# Los controles del indice se leen del estado para poder calcular los indicadores antes del mosaico
anios_disp = sorted(datos["anio"].unique())
dim_label = st.session_state.get("merc_dim", "Región de origen")
dimension = DIMENSIONES_INDICE[dim_label]
base = st.session_state.get("merc_base", 2019 if 2019 in anios_disp else anios_disp[0])
base = base if base in anios_disp else anios_disp[0]
top_n = st.session_state.get("merc_top", 8)

indice = indice_recuperacion(datos, dimension, int(base), top_n)
ultimo = indice.columns.max() if not indice.empty else None
if ultimo is not None and indice[ultimo].notna().any():
    col = indice[ultimo].dropna()
    arriba = int((col >= 100).sum())
    indicadores(
        [
            {"etiqueta": f"Por encima de {base} · {ultimo}", "valor": f"{arriba} de {len(col)}", "contexto": f"{dim_label.lower()} con índice de 100 o más"},
            {"etiqueta": f"Mayor índice · {ultimo}", "valor": f"{col.max():.0f}", "contexto": NOMBRE_CORTO.get(col.idxmax(), col.idxmax())},
            {"etiqueta": f"Índice mediano · {ultimo}", "valor": f"{col.median():.0f}", "contexto": f"entre {len(col)} categorías"},
        ]
    )

seleccion: tuple[str, int] | None = None
if "indice" in visibles:
    with mosaico(
        "indice",
        f"Índice de recuperación por {dim_label.lower().split(' /')[0]}",
        f"{base} = 100 · azul por encima, rojo por debajo · seleccione una celda para ver sus orígenes",
        "observado",
        "**¿Qué mercados ya superaron su nivel previo a la pandemia y cuáles siguen por debajo?**\n\n"
        f"Cada celda compara un año con {base}: 100 es el mismo volumen, 150 un 50 % más y 50 la mitad. Cada año "
        "se compara con los mismos meses del año base, para que un año incompleto no parezca una caída. Las celdas "
        "vacías son categorías sin viajeros en el año base. Desde 2023 la fuente agrupa algunos países en mercados, "
        "lo que también puede mover el índice por región.",
    ):
        c1, c2, c3 = st.columns(3)
        c1.selectbox("Comparar por", list(DIMENSIONES_INDICE), key="merc_dim")
        c2.selectbox("Año base", anios_disp, index=anios_disp.index(base), key="merc_base", help="2019 es el último año completo antes de la pandemia.")
        c3.slider("Filas", 3, 15, top_n, key="merc_top")
        if indice.empty or indice.isna().all().all():
            sin_datos(f"Ninguna categoría filtrada tuvo viajeros en {base}. Elija otro año base.")
        else:
            evento = st.plotly_chart(
                figura_recuperacion(indice, int(base)), key=f"indice_{dimension}_{base}", on_select="rerun",
                selection_mode="points", width="stretch",
            )
            puntos = evento.selection.points if evento and evento.selection else []
            if puntos and "y" in puntos[0] and "x" in puntos[0]:
                seleccion = (str(puntos[0]["y"]), int(puntos[0]["x"]))

if "arbol" in visibles:
    if seleccion:
        cat, anio_sel = seleccion
        detalle = datos[(datos[dimension].astype(str) == cat) & (datos["anio"] == anio_sel)]
        filtro = f"{NOMBRE_CORTO.get(cat, cat)} · {anio_sel}"
    else:
        detalle, filtro = datos, None
    with mosaico(
        "arbol",
        "Orígenes por región y país",
        f"Viajeros {'de la selección' if seleccion else f'{anios[0]}–{anios[1]}'} · clic en una región para acercarse",
        "observado",
        "**¿Qué peso tiene cada región y cada país de origen?**\n\n"
        "El área y el tono de cada rectángulo son proporcionales a sus viajeros. Un clic en una región muestra sus "
        "países; la barra superior regresa al nivel anterior.",
        filtro=filtro,
    ):
        profundidad = st.segmented_control("Nivel de detalle", ["Regiones", "Regiones y países"], default="Regiones y países", key="merc_prof") or "Regiones y países"
        if detalle.empty or detalle["viajeros"].sum() == 0:
            sin_datos("La selección no tiene viajeros registrados. Elija otra celda o restablezca con doble clic.")
        else:
            st.plotly_chart(figura_treemap(detalle, 1 if profundidad == "Regiones" else 2), key="arbol", width="stretch")
            por_region = detalle.groupby("region", observed=True)["viajeros"].sum().sort_values(ascending=False)
            por_region = por_region[por_region > 0]
            top_pais = detalle.groupby("pais", observed=True)["viajeros"].sum().nlargest(3)
            c1, c2 = st.columns(2)
            with c1:
                nota(
                    "observado",
                    f"{NOMBRE_CORTO.get(por_region.index[0], por_region.index[0])} aporta el {por_region.iloc[0] / por_region.sum():.0%} "
                    f"de los viajeros. Los tres países principales son {', '.join(f'{p} ({formato_numero(v)})' for p, v in top_pais.items())}.",
                )
            with c2:
                nota(
                    "interpretacion",
                    "Una demanda concentrada en pocos mercados simplifica la promoción, pero deja al destino expuesto a lo que "
                    "ocurra en ellos. Los datos muestran el peso de cada mercado, no la razón de sus cambios.",
                )
