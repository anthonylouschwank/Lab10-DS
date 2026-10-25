"""Pronosticos: real vs. pronostico de cada modelo (viz 7) enlazado con el error por modelo en la seleccion (viz 8).

Los pronosticos vienen de los Laboratorios 1 y 2 (src/preparar_modelos.py); aqui no se entrena nada.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.datos import NIVELES_TIEMPO
from src.estilo import MESES, formato_numero
from src.graficas import figura_error_modelos, figura_pronostico
from src.modelos import (
    DESCRIPCION_MODELO,
    METRICAS,
    ORDEN_MODELO,
    agregar_pronostico,
    cargar_pronosticos,
    cargar_series,
    tabla_metricas,
)
from src.ui import encabezado_grafica, etiqueta, selector_graficas, sin_datos

st.title("Pronósticos de llegadas")
st.markdown(
    "¿Qué tan bien habrían anticipado los modelos la llegada de viajeros? Cada modelo se entrenó con datos hasta "
    "**marzo de 2021** y pronosticó, sin ver los datos reales, de **abril 2021 a junio 2026** (periodo de prueba). "
    "Comparar el pronóstico con lo que realmente pasó muestra cuánto confiar en cada modelo."
)
st.caption(
    "Modelos de los Laboratorios 1 (Holt-Winters, SARIMA, Prophet) y 2 (LSTM). No se entrenaron modelos nuevos para este tablero."
)

pron_all = cargar_pronosticos()
series_obs = cargar_series()

series = list(dict.fromkeys(pron_all["serie"]))
c1, c2, c3 = st.columns([2, 3, 2])
serie = c1.selectbox("Serie a pronosticar", series, key="pron_serie", help="Total del país, por vía de ingreso o por frontera principal.")
pron = pron_all[pron_all["serie"] == serie]
disponibles = [m for m in ORDEN_MODELO if m in set(pron["modelo"].astype(str))]
modelos = c2.multiselect(
    "Modelos a comparar",
    disponibles,
    default=[m for m in disponibles if m != "Referencia ingenua"],
    key=f"pron_modelos_{serie}",
    help="La LSTM solo se entrenó (Laboratorio 2) para el total mensual y La Aurora.",
)
nivel = c3.segmented_control(
    "Detalle temporal", NIVELES_TIEMPO, default="Mes", key="pron_nivel", help="Suma real y pronóstico por mes, trimestre o año."
) or "Mes"

with st.expander("¿Qué es cada modelo?", icon=":material/help:"):
    for m in disponibles:
        variante = pron.loc[pron["modelo"] == m, "variante"].iloc[0]
        st.markdown(f"- **{m}** — {DESCRIPCION_MODELO[m]} _Configuración usada: {variante}._")

if pron["real"].notna().sum() == 0:
    sin_datos(
        f"**{serie}** no tiene turistas ni excursionistas registrados en el periodo de prueba (desde 2017 la fuente solo reporta cruceristas u otros tipos de viajero por esa vía), "
        "por lo que no es posible evaluar sus pronósticos. Elige otra serie."
    )
    st.stop()
if not modelos:
    sin_datos("Elige al menos un modelo en **Modelos a comparar**.")
    st.stop()

visibles = selector_graficas({"pronostico": "7. Real vs. pronóstico", "error": "8. Error por modelo"}, key="pron_vis")

pron_sel = pron[pron["modelo"].isin(modelos)]
agregado = agregar_pronostico(pron_sel, nivel)

historia = series_obs[(series_obs["serie"] == serie) & (series_obs["conjunto"] == "Entrenamiento")][["fecha", "valor"]]
if nivel != "Mes":
    historia = historia.groupby(pd.Grouper(key="fecha", freq="QS" if nivel == "Trimestre" else "YS"))["valor"].sum().reset_index()

periodos_sel: list[pd.Timestamp] = []
if "pronostico" in visibles:
    encabezado_grafica(
        7,
        f"¿Qué pronosticó cada modelo para {serie.lower()}?",
        "estimacion",
        "la línea negra con puntos es lo que realmente llegó; cada línea de color es lo que pronosticó un modelo. "
        "En gris, los datos con los que se entrenaron los modelos.",
        "ver en qué periodos cada modelo se acerca o se aleja de la realidad antes de usar sus cifras para planificar.",
    )
    con_intervalo = {"SARIMA", "Prophet"} & set(modelos)
    mostrar_intervalo = False
    if con_intervalo and nivel == "Mes":
        mostrar_intervalo = st.toggle(
            "Mostrar rango probable (95 %)",
            key="pron_intervalo",
            help="Banda dentro de la cual el modelo esperaba el valor real con 95 % de probabilidad. Solo SARIMA y Prophet la calculan.",
        )
    st.caption(
        "**Haz clic en un punto negro** (o usa la herramienta de caja para elegir un rango) para ver en la gráfica 8 "
        "qué modelo se equivocó menos en esos periodos. Doble clic limpia la selección."
    )
    evento = st.plotly_chart(
        figura_pronostico(historia, agregado, modelos, nivel, mostrar_intervalo),
        key=f"pronostico_{serie}_{nivel}",
        on_select="rerun",
        selection_mode=("points", "box"),
        use_container_width=True,
    )
    if nivel != "Mes":
        st.caption("Al agrupar, 2021 de prueba solo suma abril-diciembre (enero-marzo quedan en entrenamiento) y 2026 solo enero-junio.")
    puntos = evento.selection.points if evento and evento.selection else []
    corte = agregado["periodo"].min()
    periodos_sel = sorted({pd.Timestamp(p["x"]) for p in puntos if "x" in p and pd.Timestamp(p["x"]) >= corte})

if "error" in visibles:
    metrica = st.segmented_control(
        "Medida de error", list(METRICAS), default="MAPE", format_func=lambda k: METRICAS[k], key="pron_metrica"
    ) or "MAPE"
    if periodos_sel:
        foco = agregado[agregado["periodo"].isin(periodos_sel)]
        etiquetas = [
            str(p.year) if nivel == "Año" else (f"T{(p.month - 1) // 3 + 1} {p.year}" if nivel == "Trimestre" else f"{MESES[p.month - 1]} {p.year}")
            for p in periodos_sel
        ]
        texto = ", ".join(etiquetas) if len(etiquetas) <= 4 else f"{len(etiquetas)} periodos ({etiquetas[0]} a {etiquetas[-1]})"
    else:
        foco = agregado
        texto = "todo el periodo de prueba"
    encabezado_grafica(
        8,
        f"¿Qué modelo se equivocó menos en {texto}?",
        "estimacion",
        f"{METRICAS[metrica].lower()} de cada modelo en los periodos seleccionados en la gráfica 7. Barra más corta = mejor.",
        "elegir en qué modelo apoyarse y saber de qué tamaño es el error esperado.",
    )
    met = tabla_metricas(foco, ["modelo"])
    if met[metrica].isna().all():
        sin_datos("Los periodos seleccionados no tienen valores reales para comparar. Elige otros puntos.")
    else:
        st.plotly_chart(figura_error_modelos(met, metrica, METRICAS[metrica]), key="error_modelos", use_container_width=True)
        mejor = met.dropna(subset=[metrica]).sort_values(metrica).iloc[0]
        etiqueta("interpretacion")
        st.markdown(
            f"En {texto}, **{mejor['modelo']}** tuvo el menor error: en promedio se desvió "
            f"**{formato_numero(mejor['MAE'])} viajeros** por {nivel.lower()} (**{mejor['MAPE']:.0f} %** del valor real). "
            "Un error bajo en el pasado no garantiza el mismo desempeño a futuro."
        )
        if serie.startswith("Frontera San Cristóbal"):
            st.caption(
                "En San Cristóbal hubo meses con muy pocos viajeros: el MAPE (error en %) se dispara aunque el error en "
                "viajeros sea pequeño. Para esta serie conviene mirar el MAE."
            )

with st.expander("Ver valores en tabla", icon=":material/table:"):
    tabla = agregado.pivot_table(index="periodo", columns="modelo", values="prediccion", observed=True)
    tabla.insert(0, "Real", agregado.drop_duplicates("periodo").set_index("periodo")["real"])
    tabla.index = tabla.index.strftime("%Y-%m")
    tabla.index.name = "Periodo"
    st.dataframe(tabla.style.format("{:,.0f}", na_rep="—"), use_container_width=True)

st.info(
    "**Limitaciones.** El periodo de prueba incluye la reapertura tras la pandemia, un cambio de régimen que ningún "
    "modelo entrenado hasta marzo de 2021 podía anticipar por completo; por eso los errores son altos. "
    "Los laboratorios no generaron pronósticos posteriores a junio de 2026, así que el tablero no muestra cifras futuras.",
    icon=":material/info:",
)
