import streamlit as st

from src.datos import TIPOS_COMPARABLES, cargar_viajeros
from src.estilo import formato_numero
from src.modelos import cargar_pronosticos, tabla_metricas
from src.ui import etiqueta, nota_fuente

# Nombres cortos solo para las tarjetas (el valor completo queda en la ayuda)
NOMBRE_CORTO = {"América Del Centro": "Centroamérica", "América Del Norte": "Norteamérica"}

st.title("Observatorio de Turismo Sostenible · Guatemala")
st.markdown(
    "Tablero para directivos y tomadores de decisiones del sector turístico. "
    "Permite explorar cómo llegan los viajeros internacionales a Guatemala, de dónde vienen, "
    "en qué meses, y qué tan confiables son los modelos de pronóstico desarrollados por el equipo."
)
nota_fuente()

# ---------------------------------------------------------------- resumen (tarjetas complementarias)
df = cargar_viajeros()
d = df[df["tipo"].isin(TIPOS_COMPARABLES)]
ultimo = d["fecha"].max()
anio_completo = ultimo.year - 1 if ultimo.month < 12 else ultimo.year
por_anio = d.groupby("anio")["viajeros"].sum()
cambio_2019 = por_anio[anio_completo] / por_anio[2019] - 1
por_via = d[d["anio"] == anio_completo].groupby("via", observed=True)["viajeros"].sum()
por_region = d[d["anio"] == anio_completo].groupby("region", observed=True)["viajeros"].sum()

met = tabla_metricas(cargar_pronosticos(), ["serie", "modelo"])
total = met[(met["serie"] == "Total mensual") & (met["modelo"] != "Referencia ingenua")].sort_values("MAPE").iloc[0]

st.subheader("Resumen")
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Viajeros en {anio_completo}", formato_numero(por_anio[anio_completo]), f"{cambio_2019:+.0%} vs. 2019", border=True)
# El nombre va en la etiqueta y la cifra como valor: las tarjetas no truncan nombres largos
region = por_region.idxmax()
k2.metric(
    f"Vía {por_via.idxmax().lower()} · {anio_completo}",
    f"{por_via.max() / por_via.sum():.0%}",
    "vía principal",
    delta_color="off",
    delta_arrow="off",
    border=True,
)
k3.metric(
    f"{NOMBRE_CORTO.get(region, region)} · {anio_completo}",
    f"{por_region.max() / por_region.sum():.0%}",
    "región principal",
    delta_color="off",
    delta_arrow="off",
    border=True,
    help=f"Participación de {region} en las llegadas de {anio_completo}.",
)
k4.metric(
    f"Mejor pronóstico: {total['modelo']}",
    f"{total['MAPE']:.0f} %",
    "error promedio del total",
    delta_color="off",
    delta_arrow="off",
    border=True,
)
st.caption(f"Turistas y excursionistas. Datos hasta {ultimo:%m/%Y}; el último año completo es {anio_completo}.")

c1, c2 = st.columns(2)
with c1:
    etiqueta("observado")
    st.markdown(
        f"- En {anio_completo} llegaron **{formato_numero(por_anio[anio_completo])}** viajeros, "
        f"{abs(cambio_2019):.0%} {'más' if cambio_2019 >= 0 else 'menos'} que en 2019, el último año antes de la pandemia.\n"
        f"- En 2020 las llegadas cayeron a **{formato_numero(por_anio[2020])}** ({por_anio[2020] / por_anio[2019] - 1:+.0%} frente a 2019).\n"
        f"- La vía **{por_via.idxmax().lower()}** concentra el {por_via.max() / por_via.sum():.0%} de las llegadas y "
        f"**{por_region.idxmax()}** el {por_region.max() / por_region.sum():.0%}."
    )
    st.caption(
        "La fuente cambió en 2021 y en 2023 (ver Glosario y limitaciones): parte de la diferencia frente a 2019 puede "
        "deberse a cambios en el registro y no solo a la demanda."
    )
with c2:
    etiqueta("estimacion")
    st.markdown(
        f"- Para el total mensual, el modelo con menor error fue **{total['modelo']}**: se desvió en promedio "
        f"{formato_numero(total['MAE'])} viajeros por mes ({total['MAPE']:.0f} % del valor real) entre abril 2021 y junio 2026.\n"
        "- Ningún modelo es el mejor en todas las series: conviene elegirlo serie por serie en **Comparar modelos**.\n"
        "- Los errores son altos porque el periodo evaluado incluye la reapertura tras la pandemia."
    )

st.subheader("Preguntas que responde")
st.markdown(
    """
| Pregunta de gestión | Dónde verla |
|---|---|
| ¿Cómo ha evolucionado la llegada de viajeros y por qué vías entran? | Evolución y origen (1) |
| ¿De qué países y por qué puestos fronterizos ingresan? | Evolución y origen (2) |
| ¿En qué meses se concentra la demanda (temporadas altas y bajas)? | Temporadas (3, 4) |
| ¿Qué mercados y puestos ya superaron su nivel previo a la pandemia? | Mercados y recuperación (5) |
| ¿Qué peso tiene cada región y país de origen? | Mercados y recuperación (6) |
| ¿Cuántos viajeros pronostican los modelos y qué tan cerca estuvieron de la realidad? | Pronósticos de llegadas (7, 8) |
| ¿Qué modelo conviene usar para cada serie y hasta qué horizonte es confiable? | Comparar modelos (9, 10, 11) |
"""
)

st.subheader("Cómo navegar")
c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("paginas/explorar.py", label="Explorar los datos", icon=":material/bar_chart:")
    st.caption(
        "Tres páginas con gráficas **enlazadas**: un clic en la primera gráfica cambia el detalle de la segunda. "
        "Los filtros de arriba (años, tipo de viajero, vía) aplican a toda la página."
    )
with c2:
    st.page_link("paginas/modelos.py", label="Pronósticos y modelos", icon=":material/trending_up:")
    st.caption("Resultados de los modelos de los Laboratorios 1 y 2 y comparación de su desempeño.")
with c3:
    st.page_link("paginas/acerca.py", label="Glosario y limitaciones", icon=":material/help:")
    st.caption("Qué significa cada término y qué no se puede concluir con estos datos.")

st.markdown(
    "**Cómo leer las etiquetas:** cada gráfica indica si muestra un "
    ":blue-badge[:material/visibility: Dato observado], una "
    ":gray-badge[:material/lightbulb: Interpretación] o una "
    ":violet-badge[:material/query_stats: Estimación de modelo]. "
    "En **Gráficas visibles** puedes ocultar las que no necesites."
)
