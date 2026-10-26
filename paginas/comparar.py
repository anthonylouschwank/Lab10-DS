"""Comparar modelos: mapa de errores serie x modelo (grafica 9) filtra el error por anio (grafica 10);
ajuste de la LSTM (grafica 11) y tabla comparativa."""

from __future__ import annotations

import streamlit as st

from src.graficas import figura_error_horizonte, figura_mapa_errores, figura_tuneo
from src.modelos import METRICAS, ORDEN_MODELO, cargar_pronosticos, cargar_tuneo, tabla_metricas
from src.ui import barra_filtros, encabezado_con_vista, indicadores, mosaico, nota, sin_datos

pron = cargar_pronosticos()
tuneo = cargar_tuneo()
met = tabla_metricas(pron, ["serie", "modelo"])

visibles = encabezado_con_vista(
    "Pronósticos",
    "Comparar modelos",
    None,
    "Periodo de prueba<br><b>abr 2021 – jun 2026</b>",
    {"mapa": "Error por serie y modelo", "horizonte": "Error por año", "tuneo": "Ajuste de la LSTM"},
    "comp_vis",
)

evaluables = met.dropna(subset=["MAPE"])
candidatos = evaluables[evaluables["modelo"] != "Referencia ingenua"]
mejores = candidatos.sort_values("MAPE").groupby("serie", sort=False).head(1).set_index("serie")
referencia = evaluables[evaluables["modelo"] == "Referencia ingenua"].set_index("serie")["MAPE"]
reduccion = 1 - mejores["MAPE"] / referencia.reindex(mejores.index)
victorias = mejores["modelo"].astype(str).value_counts()
indicadores(
    [
        {"etiqueta": "Series evaluables", "valor": f"{len(mejores)} de {met['serie'].nunique()}", "contexto": "la vía marítima no tiene datos en la prueba"},
        {"etiqueta": "Menor error alcanzado", "valor": f"{mejores['MAPE'].min():.1f} %",
         "contexto": f"{mejores['MAPE'].idxmin()} · {mejores.loc[mejores['MAPE'].idxmin(), 'modelo']}"},
        {"etiqueta": "Series con mejora fuerte", "valor": f"{int((reduccion >= 2 / 3).sum())}", "contexto": "error al menos 3 veces menor que la referencia"},
        {"etiqueta": "Modelo que más series gana", "valor": victorias.index[0], "contexto": f"{victorias.iloc[0]} de {len(mejores)} series"},
    ]
)

with barra_filtros("comparar"):
    metrica = st.segmented_control(
        "Medida de error", list(METRICAS), default="MAPE", format_func=lambda k: METRICAS[k], key="comp_metrica",
        help="El MAPE compara series de distinto tamaño; el MAE y el RMSE están en viajeros.",
    ) or "MAPE"
etiqueta_metrica = METRICAS[metrica]

tabla = met.pivot_table(index="serie", columns="modelo", values=metrica, observed=False, dropna=False)
tabla = tabla.reindex(index=list(dict.fromkeys(pron["serie"])), columns=ORDEN_MODELO)

if {"mapa", "horizonte"} <= visibles:
    col_a, col_b = st.columns([1.15, 1], gap="small")
else:
    col_a = col_b = st.container()

serie_sel = "Total mensual"
if "mapa" in visibles:
    with col_a, mosaico(
        "mapa",
        "Error por serie y modelo",
        f"{etiqueta_metrica} · más oscuro, más error · seleccione una celda para ver su evolución",
        "estimacion",
        "**¿Qué modelo conviene en cada serie?**\n\n"
        "Las filas son series y las columnas, modelos. La última columna es la referencia ingenua, que repite el "
        "último año conocido: un modelo útil debe quedar por debajo de ella. «Sin dato» indica que el modelo no se "
        "entrenó para esa serie o que la serie no tiene datos reales en la prueba.",
    ):
        evento = st.plotly_chart(figura_mapa_errores(tabla, metrica, etiqueta_metrica), key=f"mapa_{metrica}", on_select="rerun", selection_mode="points", width="stretch")
        puntos = evento.selection.points if evento and evento.selection else []
        if puntos and "y" in puntos[0]:
            serie_sel = str(puntos[0]["y"])

if "horizonte" in visibles:
    with col_b, mosaico(
        "horizonte",
        "Error por año de la prueba",
        f"{etiqueta_metrica} · 2021 cubre abr-dic y 2026 ene-jun",
        "estimacion",
        "**¿El error crece a medida que el pronóstico se aleja del corte?**\n\n"
        "Cada línea sigue el error de un modelo en cada año del periodo de prueba. Una línea que sube indica que el "
        "modelo pierde precisión con el horizonte y que convendría actualizarlo con más frecuencia.",
        filtro=serie_sel if "mapa" in visibles else None,
    ):
        if "mapa" not in visibles:
            serie_sel = st.selectbox("Serie", list(tabla.index), key="comp_serie")
        p = pron[pron["serie"] == serie_sel]
        if p["real"].notna().sum() == 0:
            sin_datos(f"{serie_sel} no tiene datos reales en el periodo de prueba, así que no se puede medir su error.")
        else:
            por_anio = tabla_metricas(p.assign(anio=p["fecha"].dt.year), ["modelo", "anio"])
            st.plotly_chart(figura_error_horizonte(por_anio, metrica, etiqueta_metrica), key="horizonte", width="stretch")
            promedio = por_anio[por_anio["modelo"] != "Referencia ingenua"].groupby("anio")[metrica].mean().dropna()
            if not promedio.empty:
                nota("observado", f"Con el promedio de los modelos, {promedio.idxmax()} fue el año con más error y {promedio.idxmin()} el de menos.")

if {"tuneo"} <= visibles:
    col_c, col_d = st.columns([1, 1.15], gap="small")
else:
    col_c = col_d = st.container()

if "tuneo" in visibles:
    series_lstm = list(dict.fromkeys(tuneo["serie"]))
    with col_c, mosaico(
        "tuneo",
        "Ajuste de la red LSTM",
        "Error de validación (RMSE) por configuración · en verde, la elegida",
        "estimacion",
        "**¿Cómo se eligió la configuración de la LSTM?**\n\n"
        "Cada barra es una configuración probada en el Laboratorio 2. Su altura es el error en los datos de "
        "validación, meses previos al corte que la red no usó para aprender. Se eligió la de menor error, sin tocar "
        "el periodo de prueba. Al pasar el cursor se ven la ventana, las unidades, el dropout, la tasa de aprendizaje "
        "y la época en que se detuvo el entrenamiento.",
    ):
        serie_t = st.segmented_control("Serie", series_lstm, default=series_lstm[0], key="comp_tuneo") or series_lstm[0]
        t = tuneo[tuneo["serie"] == serie_t]
        st.plotly_chart(figura_tuneo(t, t.sort_values("val_RMSE")["modelo"].iloc[0]), key=f"tuneo_{serie_t}", width="stretch")

with col_d, st.container(key="tile-tabla"):
    st.html('<div class="ot-tt">Resumen por serie y modelo</div><div class="ot-ts">MAE y RMSE en viajeros por mes; MAPE en porcentaje</div>')
    comp = met.copy()
    comp["modelo"] = comp["modelo"].astype(str)
    comp = comp.merge(pron[["serie", "modelo", "variante", "laboratorio"]].astype({"modelo": str}).drop_duplicates(), on=["serie", "modelo"])
    comp = comp.rename(columns={"serie": "Serie", "modelo": "Modelo", "variante": "Configuración", "laboratorio": "Origen"})
    st.dataframe(
        comp[["Serie", "Modelo", "MAPE", "MAE", "RMSE", "Origen", "Configuración"]].style.format(
            {"MAE": "{:,.0f}", "RMSE": "{:,.0f}", "MAPE": "{:.1f} %"}, na_rep="—"
        ),
        hide_index=True, width="stretch", height=430,
    )
