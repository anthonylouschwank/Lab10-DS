"""Comparar modelos: mapa de errores serie x modelo (grafica 9) enlazado con el error por anio (grafica 10),
ajuste de la LSTM (grafica 11) y tabla comparativa (complementaria)."""

from __future__ import annotations

import streamlit as st

from src.graficas import figura_error_horizonte, figura_mapa_errores, figura_tuneo
from src.modelos import METRICAS, ORDEN_MODELO, cargar_pronosticos, cargar_tuneo, tabla_metricas
from src.ui import barra_filtros, encabezado_pagina, hallazgo, indicadores, selector_graficas, sin_datos, tarjeta_grafica

encabezado_pagina(
    "Pronósticos · 2 de 2",
    "Comparar modelos",
    "Qué modelo conviene usar en cada serie y hasta dónde es confiable. Todos los errores se midieron en el mismo "
    "periodo de prueba, de abril de 2021 a junio de 2026, de modo que la comparación es directa.",
)

pron = cargar_pronosticos()
tuneo = cargar_tuneo()
met = tabla_metricas(pron, ["serie", "modelo"])

# Sintesis: mejor modelo por serie frente a la referencia ingenua
evaluables = met.dropna(subset=["MAPE"])
candidatos = evaluables[evaluables["modelo"] != "Referencia ingenua"]
mejores = candidatos.sort_values("MAPE").groupby("serie", sort=False).head(1).set_index("serie")
referencia = evaluables[evaluables["modelo"] == "Referencia ingenua"].set_index("serie")["MAPE"]
reduccion = 1 - mejores["MAPE"] / referencia.reindex(mejores.index)
fuertes = int((reduccion >= 2 / 3).sum())
total_series = met["serie"].nunique()
indicadores(
    [
        ("Series evaluables", f"{len(mejores)} de {total_series}", "la vía marítima no tiene datos reales en la prueba"),
        ("Menor error alcanzado", f"{mejores['MAPE'].min():.1f} %", f"{mejores['MAPE'].idxmin()} · {mejores.loc[mejores['MAPE'].idxmin(), 'modelo']}"),
        ("Mejora fuerte sobre la referencia", f"{fuertes} series", "el mejor modelo reduce el error en dos tercios o más"),
    ]
)

with barra_filtros("comparar"):
    metrica = st.segmented_control(
        "Medida de error", list(METRICAS), default="MAPE", format_func=lambda k: METRICAS[k], key="comp_metrica",
        help="El MAPE permite comparar series de distinto tamaño; el MAE y el RMSE están en viajeros.",
    ) or "MAPE"
    visibles = selector_graficas(
        {"mapa": "9 · Error por serie y modelo", "horizonte": "10 · Error año por año", "tuneo": "11 · Ajuste de la LSTM"},
        key="comp_vis",
    )
etiqueta_metrica = METRICAS[metrica]

tabla = met.pivot_table(index="serie", columns="modelo", values=metrica, observed=False, dropna=False)
tabla = tabla.reindex(index=list(dict.fromkeys(pron["serie"])), columns=ORDEN_MODELO)

serie_sel = "Total mensual"
if "mapa" in visibles:
    with tarjeta_grafica(
        9,
        "¿Qué modelo se equivocó menos en cada serie?",
        "estimacion",
        "Sirve para elegir el modelo más confiable para cada serie que se quiera planificar.",
        "Las filas son series y las columnas, modelos. Cada celda muestra el error del modelo en esa serie: cuanto "
        "más oscuro el azul, mayor el error. La última columna es la referencia ingenua, que repite el último año "
        "conocido; un modelo útil debe quedar por debajo de ella. «Sin dato» indica que el modelo no se entrenó para "
        "esa serie o que la serie no tiene datos reales en la prueba.\n\n"
        "**Para profundizar:** haga clic en una celda y la gráfica 10 mostrará la evolución del error de esa serie año por año.",
        "<b>Clic en una celda</b> para ver el error de esa serie año por año en la gráfica 10",
    ):
        evento = st.plotly_chart(
            figura_mapa_errores(tabla, metrica, etiqueta_metrica), key=f"mapa_{metrica}", on_select="rerun",
            selection_mode="points", width="stretch",
        )
        puntos = evento.selection.points if evento and evento.selection else []
        if puntos and "y" in puntos[0]:
            serie_sel = str(puntos[0]["y"])
        mejor_por_serie = met.dropna(subset=[metrica]).sort_values(metrica).groupby("serie", sort=False).head(1)
        hallazgo(
            "estimacion",
            "Mejor modelo por serie: "
            + "; ".join(f"{r.serie}, **{r.modelo}** ({getattr(r, metrica):,.1f}{' %' if metrica == 'MAPE' else ''})" for r in mejor_por_serie.itertuples())
            + ".",
        )

if "horizonte" in visibles:
    with tarjeta_grafica(
        10,
        f"¿El error crece al alejarse del corte? · {serie_sel}",
        "estimacion",
        "Sirve para saber hasta qué horizonte un pronóstico es razonable y cuándo conviene actualizar el modelo.",
        "Cada línea sigue el error de un modelo en cada año del periodo de prueba (2021 cubre de abril a diciembre "
        "y 2026, de enero a junio). Una línea que sube indica que el modelo pierde precisión a medida que se aleja "
        "de los datos con los que aprendió.",
    ):
        if "mapa" not in visibles:
            serie_sel = st.selectbox("Serie", list(tabla.index), key="comp_serie")
        p = pron[pron["serie"] == serie_sel]
        if p["real"].notna().sum() == 0:
            sin_datos(f"**{serie_sel}** no tiene datos reales en el periodo de prueba, así que no se puede medir su error. Elija otra serie.")
        else:
            por_anio = tabla_metricas(p.assign(anio=p["fecha"].dt.year), ["modelo", "anio"])
            st.plotly_chart(figura_error_horizonte(por_anio, metrica, etiqueta_metrica), key="horizonte", width="stretch")
            promedio = por_anio[por_anio["modelo"] != "Referencia ingenua"].groupby("anio")[metrica].mean().dropna()
            if not promedio.empty:
                c1, c2 = st.columns(2)
                with c1:
                    hallazgo(
                        "observado",
                        f"Con el promedio de los modelos, {promedio.idxmax()} fue el año con más error y {promedio.idxmin()}, el de menos.",
                    )
                with c2:
                    hallazgo(
                        "interpretacion",
                        "Los modelos aprendieron con datos hasta marzo de 2021 y no podían conocer el ritmo de la reapertura. "
                        "Es razonable que fallen más en los años en que el flujo cambió con mayor rapidez.",
                    )

if "tuneo" in visibles:
    series_lstm = list(dict.fromkeys(tuneo["serie"]))
    with tarjeta_grafica(
        11,
        "¿Cómo se eligió la configuración de la red LSTM?",
        "estimacion",
        "Sirve para comprobar que la LSTM se eligió sin mirar el periodo de prueba y ver qué tanto depende de su configuración.",
        "Cada barra es una configuración probada en el Laboratorio 2. Su altura es el error en los datos de "
        "validación: meses previos al corte que la red no usó para aprender. En verde, la configuración elegida, "
        "la de menor error. Al pasar el cursor se ven la ventana, las unidades, el dropout, la tasa de aprendizaje y "
        "la época en que se detuvo el entrenamiento.",
    ):
        serie_t = st.segmented_control("Serie", series_lstm, default=series_lstm[0], key="comp_tuneo") or series_lstm[0]
        t = tuneo[tuneo["serie"] == serie_t]
        st.plotly_chart(figura_tuneo(t, t.sort_values("val_RMSE")["modelo"].iloc[0]), key=f"tuneo_{serie_t}", width="stretch")

with st.container(border=True, key="tarjeta-tabla"):
    st.html(
        '<div class="op-q">Tabla comparativa de modelos</div>'
        '<div class="op-sub">Todas las medidas corresponden al periodo de prueba. MAE y RMSE en viajeros por mes; MAPE en porcentaje.</div>'
    )
    comp = met.copy()
    comp["modelo"] = comp["modelo"].astype(str)
    comp = comp.merge(pron[["serie", "modelo", "variante", "laboratorio"]].astype({"modelo": str}).drop_duplicates(), on=["serie", "modelo"])
    comp = comp.rename(columns={"serie": "Serie", "modelo": "Modelo", "variante": "Configuración", "laboratorio": "Origen", "meses": "Meses evaluados"})
    st.dataframe(
        comp[["Serie", "Modelo", "Configuración", "Origen", "MAE", "RMSE", "MAPE", "Meses evaluados"]].style.format(
            {"MAE": "{:,.0f}", "RMSE": "{:,.0f}", "MAPE": "{:.1f} %", "Meses evaluados": "{:.0f}"}, na_rep="—"
        ),
        hide_index=True,
        width="stretch",
    )
