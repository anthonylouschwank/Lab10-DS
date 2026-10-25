"""Comparar modelos: mapa de errores serie x modelo (viz 9) enlazado con el error por anio (viz 10),
tuneo de la LSTM (viz 11) y tabla comparativa (complementaria)."""

from __future__ import annotations

import streamlit as st

from src.graficas import figura_error_horizonte, figura_mapa_errores, figura_tuneo
from src.modelos import METRICAS, ORDEN_MODELO, cargar_pronosticos, cargar_tuneo, tabla_metricas
from src.ui import encabezado_grafica, etiqueta, selector_graficas, sin_datos

st.title("Comparar modelos")
st.markdown(
    "¿Qué modelo conviene usar para cada serie y qué tan confiable es? Todos los errores se miden en el mismo "
    "periodo de prueba (abril 2021 - junio 2026), así que las comparaciones son justas."
)

pron = cargar_pronosticos()
tuneo = cargar_tuneo()

metrica = st.segmented_control(
    "Medida de error", list(METRICAS), default="MAPE", format_func=lambda k: METRICAS[k], key="comp_metrica",
    help="MAPE permite comparar series de distinto tamaño; MAE y RMSE están en viajeros.",
) or "MAPE"
etiqueta_metrica = METRICAS[metrica]

visibles = selector_graficas(
    {"mapa": "9. Error por serie y modelo", "horizonte": "10. Error año por año", "tuneo": "11. Ajuste de la LSTM"},
    key="comp_vis",
)

met = tabla_metricas(pron, ["serie", "modelo"])
tabla = met.pivot_table(index="serie", columns="modelo", values=metrica, observed=False, dropna=False)
tabla = tabla.reindex(index=list(dict.fromkeys(pron["serie"])), columns=ORDEN_MODELO)

serie_sel = "Total mensual"
if "mapa" in visibles:
    encabezado_grafica(
        9,
        "¿Qué modelo se equivocó menos en cada serie?",
        "estimacion",
        f"{etiqueta_metrica.lower()} de cada modelo (columnas) en cada serie (filas). Azul más oscuro = más error. "
        "«sin dato»: el modelo no se entrenó para esa serie o la serie no tiene datos reales en la prueba.",
        "elegir, para cada serie que se quiera planificar, el modelo más confiable y compararlo contra la referencia ingenua.",
    )
    st.caption("**Haz clic en una celda** para ver en la gráfica 10 cómo evolucionó el error de esa serie año por año.")
    evento = st.plotly_chart(
        figura_mapa_errores(tabla, metrica, etiqueta_metrica), key=f"mapa_{metrica}", on_select="rerun",
        selection_mode="points", use_container_width=True,
    )
    puntos = evento.selection.points if evento and evento.selection else []
    if puntos and "y" in puntos[0]:
        serie_sel = str(puntos[0]["y"])

    mejores = met.dropna(subset=[metrica]).sort_values(metrica).groupby("serie", sort=False).head(1)
    etiqueta("estimacion")
    st.markdown(
        "**Mejor modelo por serie:** "
        + "; ".join(f"{r.serie} → **{r.modelo}** ({getattr(r, metrica):,.1f}{' %' if metrica == 'MAPE' else ''})" for r in mejores.itertuples())
        + "."
    )

if "horizonte" in visibles:
    encabezado_grafica(
        10,
        f"¿El error crece al alejarse del corte? — {serie_sel}",
        "estimacion",
        f"{etiqueta_metrica.lower()} de cada modelo en cada año del periodo de prueba (2021 = abr-dic; 2026 = ene-jun).",
        "saber hasta qué horizonte es razonable confiar en un pronóstico y cuándo conviene actualizar el modelo.",
    )
    if not ("mapa" in visibles):
        serie_sel = st.selectbox("Serie", list(tabla.index), key="comp_serie")
    p = pron[pron["serie"] == serie_sel]
    if p["real"].notna().sum() == 0:
        sin_datos(f"**{serie_sel}** no tiene datos reales en el periodo de prueba; no se puede medir el error. Elige otra celda.")
    else:
        por_anio = tabla_metricas(p.assign(anio=p["fecha"].dt.year), ["modelo", "anio"])
        st.plotly_chart(figura_error_horizonte(por_anio, metrica, etiqueta_metrica), key="horizonte", use_container_width=True)
        promedio = por_anio[por_anio["modelo"] != "Referencia ingenua"].groupby("anio")[metrica].mean().dropna()
        if not promedio.empty:
            etiqueta("observado")
            st.markdown(
                f"Promediando los modelos, el año con más error fue **{promedio.idxmax()}** y el de menos error **{promedio.idxmin()}**."
            )
            etiqueta("interpretacion")
            st.markdown(
                "Los modelos se entrenaron con datos hasta marzo de 2021 y no podían conocer el ritmo de la reapertura; "
                "es esperable que se equivoquen más en los años en que el flujo cambió más rápido."
            )

if "tuneo" in visibles:
    series_lstm = list(dict.fromkeys(tuneo["serie"]))
    encabezado_grafica(
        11,
        "¿Cómo se eligió la configuración de la red LSTM?",
        "estimacion",
        "el error en datos de validación (meses previos al corte que la red no usó para aprender) de cada configuración probada en el Laboratorio 2. "
        "En verde, la elegida: la de menor error.",
        "entender que la LSTM se eligió con datos separados de la prueba y qué tan sensible es a su configuración.",
    )
    serie_t = st.segmented_control("Serie", series_lstm, default=series_lstm[0], key="comp_tuneo") or series_lstm[0]
    t = tuneo[tuneo["serie"] == serie_t]
    elegido = t.sort_values("val_RMSE")["modelo"].iloc[0]
    st.plotly_chart(figura_tuneo(t, elegido), key=f"tuneo_{serie_t}", use_container_width=True)
    st.caption("Pasa el cursor sobre una barra para ver la ventana, las unidades, el dropout, la tasa de aprendizaje y la época en que se detuvo el entrenamiento.")

st.subheader("Tabla comparativa de modelos")
st.caption("Todas las medidas sobre el periodo de prueba. MAE y RMSE en viajeros por mes; MAPE en %.")
comp = met.copy()
comp["modelo"] = comp["modelo"].astype(str)
comp = comp.merge(pron[["serie", "modelo", "variante", "laboratorio"]].astype({"modelo": str}).drop_duplicates(), on=["serie", "modelo"])
comp = comp.rename(columns={"serie": "Serie", "modelo": "Modelo", "variante": "Configuración", "laboratorio": "Origen", "meses": "Meses evaluados"})
st.dataframe(
    comp[["Serie", "Modelo", "Configuración", "Origen", "MAE", "RMSE", "MAPE", "Meses evaluados"]].style.format(
        {"MAE": "{:,.0f}", "RMSE": "{:,.0f}", "MAPE": "{:.1f} %", "Meses evaluados": "{:.0f}"}, na_rep="—"
    ),
    hide_index=True,
    use_container_width=True,
)
st.info(
    "**Cómo leer estos resultados.** Ningún modelo es el mejor en todas las series. La referencia ingenua es la vara mínima: "
    "un modelo que no la supera no aporta información adicional. Los errores altos reflejan sobre todo la reapertura "
    "posterior a la pandemia, que ocurrió dentro del periodo de prueba.",
    icon=":material/info:",
)
