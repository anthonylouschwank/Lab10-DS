"""Pronosticos: real vs. pronostico de cada modelo (grafica 7) enlazado con el error por modelo en la seleccion (grafica 8).

Los pronosticos vienen de los Laboratorios 1 y 2 (src/preparar_modelos.py); aqui no se entrena nada.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.datos import NIVELES_TIEMPO
from src.estilo import MESES, formato_numero
from src.graficas import figura_error_modelos, figura_pronostico
from src.modelos import DESCRIPCION_MODELO, METRICAS, ORDEN_MODELO, agregar_pronostico, cargar_pronosticos, cargar_series, tabla_metricas
from src.ui import barra_filtros, encabezado_pagina, hallazgo, selector_graficas, sin_datos, tarjeta_grafica

encabezado_pagina(
    "Pronósticos · 1 de 2",
    "Pronósticos de llegadas",
    "Los modelos aprendieron con datos hasta <b>marzo de 2021</b> y pronosticaron de <b>abril de 2021 a junio de 2026</b> "
    "sin ver lo que realmente ocurrió. Comparar ambas cosas indica cuánto se puede confiar en cada uno.",
)

pron_all = cargar_pronosticos()
series_obs = cargar_series()
series = list(dict.fromkeys(pron_all["serie"]))

with barra_filtros("pronosticos"):
    c1, c2, c3 = st.columns([1.3, 2, 1.2], gap="medium")
    serie = c1.selectbox("Serie", series, key="pron_serie", help="El total del país, cada vía de ingreso o una de las tres fronteras principales.")
    pron = pron_all[pron_all["serie"] == serie]
    disponibles = [m for m in ORDEN_MODELO if m in set(pron["modelo"].astype(str))]
    modelos = c2.multiselect(
        "Modelos a comparar", disponibles, default=[m for m in disponibles if m != "Referencia ingenua"], key=f"pron_modelos_{serie}",
        help="La LSTM (Laboratorio 2) solo se entrenó para el total mensual y para La Aurora.",
    )
    nivel = c3.segmented_control(
        "Detalle temporal", NIVELES_TIEMPO, default="Mes", key="pron_nivel", help="Suma lo real y lo pronosticado por mes, trimestre o año."
    ) or "Mes"
    visibles = selector_graficas({"pronostico": "7 · Real frente a pronóstico", "error": "8 · Error por modelo"}, key="pron_vis")

with st.expander("Qué hace cada modelo", icon=":material/model_training:"):
    for m in disponibles:
        variante = pron.loc[pron["modelo"] == m, "variante"].iloc[0]
        st.markdown(f"**{m}.** {DESCRIPCION_MODELO[m]} <span style='color:#6b6a66'>Configuración: {variante}.</span>", unsafe_allow_html=True)

if pron["real"].notna().sum() == 0:
    sin_datos(
        f"**{serie}** no tiene turistas ni excursionistas registrados en el periodo de prueba: desde 2017 la fuente solo "
        "reporta cruceristas y otros tipos de viajero por esa vía. Sin datos reales no es posible evaluar sus pronósticos; elija otra serie."
    )
    st.stop()
if not modelos:
    sin_datos("Elija al menos un modelo en **Modelos a comparar**.")
    st.stop()

agregado = agregar_pronostico(pron[pron["modelo"].isin(modelos)], nivel)
historia = series_obs[(series_obs["serie"] == serie) & (series_obs["conjunto"] == "Entrenamiento")][["fecha", "valor"]]
if nivel != "Mes":
    historia = historia.groupby(pd.Grouper(key="fecha", freq="QS" if nivel == "Trimestre" else "YS"))["valor"].sum().reset_index()


def etiqueta_periodo(p: pd.Timestamp) -> str:
    if nivel == "Año":
        return str(p.year)
    if nivel == "Trimestre":
        return f"T{(p.month - 1) // 3 + 1} {p.year}"
    return f"{MESES[p.month - 1]} {p.year}"


periodos_sel: list[pd.Timestamp] = []
if "pronostico" in visibles:
    with tarjeta_grafica(
        7,
        f"¿Qué pronosticó cada modelo para {serie.lower()}?",
        "estimacion",
        "Sirve para ver en qué periodos cada modelo se acerca a la realidad antes de usar sus cifras para planificar.",
        "La línea negra con puntos es lo que realmente llegó; cada línea de color, lo que pronosticó un modelo, con su "
        "propio tipo de trazo. En gris, la historia con la que se entrenaron. La línea vertical marca el inicio del "
        "periodo de prueba.\n\n"
        "El **rango probable** es la banda donde el modelo esperaba encontrar el valor real con 95 % de probabilidad; "
        "solo SARIMA y Prophet lo calculan.\n\n"
        "**Para profundizar:** haga clic en un punto negro, o seleccione un rango con la herramienta de caja, y la "
        "gráfica 8 calculará el error de cada modelo en esos periodos.",
        "<b>Clic en un punto negro</b> o selección por caja para evaluar ese periodo en la gráfica 8",
    ):
        mostrar_intervalo = False
        if {"SARIMA", "Prophet"} & set(modelos) and nivel == "Mes":
            mostrar_intervalo = st.toggle("Mostrar rango probable (95 %)", key="pron_intervalo")
        evento = st.plotly_chart(
            figura_pronostico(historia, agregado, modelos, nivel, mostrar_intervalo),
            key=f"pronostico_{serie}_{nivel}", on_select="rerun", selection_mode=("points", "box"), width="stretch",
        )
        if nivel != "Mes":
            st.caption("Al agrupar, el 2021 de prueba solo suma de abril a diciembre (enero a marzo pertenecen al entrenamiento) y 2026, de enero a junio.")
        puntos = evento.selection.points if evento and evento.selection else []
        corte = agregado["periodo"].min()
        periodos_sel = sorted({pd.Timestamp(p["x"]) for p in puntos if "x" in p and pd.Timestamp(p["x"]) >= corte})

if "error" in visibles:
    if periodos_sel:
        foco = agregado[agregado["periodo"].isin(periodos_sel)]
        etiquetas = [etiqueta_periodo(p) for p in periodos_sel]
        texto = ", ".join(etiquetas) if len(etiquetas) <= 4 else f"{len(etiquetas)} periodos ({etiquetas[0]} a {etiquetas[-1]})"
    else:
        foco = agregado
        texto = "todo el periodo de prueba"
    with tarjeta_grafica(
        8,
        f"¿Qué modelo se equivocó menos en {texto}?",
        "estimacion",
        "Sirve para decidir en qué modelo apoyarse y conocer el tamaño del error que cabe esperar.",
        "Cada barra es el error promedio de un modelo en los periodos elegidos en la gráfica 7; la más corta es la "
        "mejor. **MAPE** expresa el error como porcentaje del valor real; **MAE**, en viajeros; **RMSE** también en "
        "viajeros, pero castiga más los errores grandes.",
    ):
        metrica = st.segmented_control(
            "Medida de error", list(METRICAS), default="MAPE", format_func=lambda k: METRICAS[k], key="pron_metrica"
        ) or "MAPE"
        met = tabla_metricas(foco, ["modelo"])
        if met[metrica].isna().all():
            sin_datos("Los periodos seleccionados no tienen valores reales para comparar. Elija otros puntos.")
        else:
            st.plotly_chart(figura_error_modelos(met, metrica, METRICAS[metrica]), key="error_modelos", width="stretch")
            mejor = met.dropna(subset=[metrica]).sort_values(metrica).iloc[0]
            c1, c2 = st.columns(2)
            with c1:
                hallazgo(
                    "estimacion",
                    f"En {texto}, **{mejor['modelo']}** fue el modelo con menor error: se desvió en promedio "
                    f"{formato_numero(mejor['MAE'])} viajeros por {nivel.lower()}, el {mejor['MAPE']:.0f} % del valor real.",
                )
            with c2:
                hallazgo(
                    "interpretacion",
                    "El periodo de prueba incluye la reapertura posterior a la pandemia, un cambio que ningún modelo "
                    "entrenado hasta marzo de 2021 podía anticipar del todo. Un buen desempeño pasado no garantiza el futuro."
                    + (" En San Cristóbal hubo meses con muy pocos viajeros, lo que dispara el MAPE; para esta serie conviene mirar el MAE."
                       if serie.startswith("Frontera San Cristóbal") else ""),
                )

with st.expander("Ver los valores en tabla", icon=":material/table:"):
    tabla = agregado.pivot_table(index="periodo", columns="modelo", values="prediccion", observed=True)
    tabla.insert(0, "Real", agregado.drop_duplicates("periodo").set_index("periodo")["real"])
    tabla.index = tabla.index.strftime("%Y-%m")
    tabla.index.name = "Periodo"
    st.dataframe(tabla.style.format("{:,.0f}", na_rep="—"), width="stretch")

st.caption("Los laboratorios no generaron pronósticos posteriores a junio de 2026, por lo que el tablero no muestra cifras futuras.")
