"""Pronosticos: real vs. pronostico de cada modelo (grafica 7) filtra el error por modelo (grafica 8).

Los pronosticos vienen de los Laboratorios 1 y 2 (src/preparar_modelos.py); aqui no se entrena nada.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.datos import NIVELES_TIEMPO
from src.estilo import MESES, formato_numero
from src.graficas import figura_error_modelos, figura_pronostico
from src.modelos import DESCRIPCION_MODELO, METRICAS, ORDEN_MODELO, agregar_pronostico, cargar_pronosticos, cargar_series, tabla_metricas
from src.ui import barra_filtros, encabezado_con_vista, indicadores, mosaico, nota, sin_datos

pron_all = cargar_pronosticos()
series_obs = cargar_series()
series = list(dict.fromkeys(pron_all["serie"]))

visibles = encabezado_con_vista(
    "Pronósticos",
    "Pronósticos de llegadas",
    None,
    "Entrenamiento <b>ene 2009 – mar 2021</b><br>Prueba <b>abr 2021 – jun 2026</b>",
    {"pronostico": "Real frente a pronóstico", "error": "Error por modelo"},
    "pron_vis",
)

with barra_filtros("pronosticos"):
    c1, c2, c3 = st.columns([1.2, 2.1, 1.1], gap="medium")
    serie = c1.selectbox("Serie", series, key="pron_serie")
    pron = pron_all[pron_all["serie"] == serie]
    disponibles = [m for m in ORDEN_MODELO if m in set(pron["modelo"].astype(str))]
    modelos = c2.multiselect(
        "Modelos", disponibles, default=[m for m in disponibles if m != "Referencia ingenua"], key=f"pron_modelos_{serie}",
        help="La LSTM (Laboratorio 2) solo se entrenó para el total mensual y para La Aurora.",
    )
    nivel = c3.segmented_control("Detalle temporal", NIVELES_TIEMPO, default="Mes", key="pron_nivel") or "Mes"

if pron["real"].notna().sum() == 0:
    sin_datos(
        f"{serie} no tiene turistas ni excursionistas registrados en el periodo de prueba: desde 2017 la fuente solo "
        "reporta cruceristas y otros tipos de viajero por esa vía. Sin datos reales no es posible evaluar sus pronósticos."
    )
    st.stop()
if not modelos:
    sin_datos("Elija al menos un modelo en **Modelos**.")
    st.stop()

met_serie = tabla_metricas(pron, ["modelo"]).dropna(subset=["MAPE"])
candidatos = met_serie[met_serie["modelo"] != "Referencia ingenua"].sort_values("MAPE")
lider = candidatos.iloc[0]
ref = met_serie.loc[met_serie["modelo"] == "Referencia ingenua", "MAPE"]
real_mensual = pron.drop_duplicates("fecha").sort_values("fecha")["real"]
indicadores(
    [
        {"etiqueta": "Modelo con menor error", "valor": str(lider["modelo"]), "contexto": f"{serie} · periodo de prueba"},
        {"etiqueta": "Error porcentual promedio", "valor": f"{lider['MAPE']:.1f} %",
         "contexto": f"referencia ingenua: {ref.iloc[0]:.1f} %" if not ref.empty else ""},
        {"etiqueta": "Error promedio en viajeros", "valor": formato_numero(lider["MAE"]), "contexto": "por mes"},
        {"etiqueta": "Viajeros reales en la prueba", "valor": formato_numero(real_mensual.sum()), "contexto": f"{len(real_mensual)} meses", "serie": real_mensual.tolist()},
    ]
)

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


if {"pronostico", "error"} <= visibles:
    col_a, col_b = st.columns([1.7, 1], gap="small")
else:
    col_a = col_b = st.container()

periodos_sel: list[pd.Timestamp] = []
if "pronostico" in visibles:
    with col_a, mosaico(
        "pronostico",
        f"Real frente a pronóstico · {serie}",
        "Viajeros por " + {"Año": "año", "Trimestre": "trimestre", "Mes": "mes"}[nivel] + " · seleccione puntos para evaluar ese periodo",
        "estimacion",
        "**¿Qué pronosticó cada modelo y qué tan cerca quedó de lo que ocurrió?**\n\n"
        "La línea negra con puntos es lo real; cada línea de color, un modelo, con su propio trazo. En gris está la "
        "historia con la que se entrenaron y la línea vertical marca el inicio de la prueba. El rango probable es la "
        "banda donde el modelo esperaba el valor real con 95 % de probabilidad (solo SARIMA y Prophet la calculan). "
        "Al seleccionar puntos negros, la gráfica de error se recalcula para esos periodos.\n\n"
        + "\n".join(f"- **{m}.** {DESCRIPCION_MODELO[m]}" for m in disponibles),
    ):
        mostrar_intervalo = False
        if {"SARIMA", "Prophet"} & set(modelos) and nivel == "Mes":
            mostrar_intervalo = st.toggle("Rango probable (95 %)", key="pron_intervalo")
        evento = st.plotly_chart(
            figura_pronostico(historia, agregado, modelos, nivel, mostrar_intervalo),
            key=f"pronostico_{serie}_{nivel}", on_select="rerun", selection_mode=("points", "box"), width="stretch",
        )
        if nivel != "Mes":
            st.caption("2021 suma solo abril a diciembre y 2026, enero a junio.")
        puntos = evento.selection.points if evento and evento.selection else []
        corte = agregado["periodo"].min()
        periodos_sel = sorted({pd.Timestamp(p["x"]) for p in puntos if "x" in p and pd.Timestamp(p["x"]) >= corte})

if "error" in visibles:
    if periodos_sel:
        foco = agregado[agregado["periodo"].isin(periodos_sel)]
        etiquetas = [etiqueta_periodo(p) for p in periodos_sel]
        filtro = ", ".join(etiquetas) if len(etiquetas) <= 3 else f"{etiquetas[0]} a {etiquetas[-1]}"
    else:
        foco, filtro = agregado, None
    with col_b, mosaico(
        "error",
        "Error por modelo",
        "Promedio en el periodo de prueba" if not filtro else f"Promedio en {len(periodos_sel)} periodo(s) seleccionado(s)",
        "estimacion",
        "**¿Qué modelo se equivocó menos?**\n\n"
        "Cada barra es el error promedio de un modelo; la más corta es la mejor. **MAPE** es el error como porcentaje "
        "del valor real, **MAE** el error en viajeros y **RMSE** también en viajeros, pero castiga más los errores "
        "grandes. En series con meses de muy pocos viajeros, como San Cristóbal, el MAPE se dispara y conviene mirar el MAE.",
        filtro=filtro,
    ):
        metrica = st.segmented_control("Medida", list(METRICAS), default="MAPE", key="pron_metrica") or "MAPE"
        met = tabla_metricas(foco, ["modelo"])
        if met[metrica].isna().all():
            sin_datos("Los periodos seleccionados no tienen valores reales para comparar. Elija otros puntos.")
        else:
            st.plotly_chart(figura_error_modelos(met, metrica, METRICAS[metrica]), key="error_modelos", width="stretch")
            mejor = met.dropna(subset=[metrica]).sort_values(metrica).iloc[0]
            nota(
                "estimacion",
                f"{mejor['modelo']} se desvió en promedio {formato_numero(mejor['MAE'])} viajeros por "
                f"{ {'Año': 'año', 'Trimestre': 'trimestre', 'Mes': 'mes'}[nivel] }, el {mejor['MAPE']:.0f} % del valor real.",
            )
            nota(
                "interpretacion",
                "La prueba arranca en plena reapertura, un cambio que ningún modelo entrenado hasta marzo de 2021 podía prever. "
                "Un buen resultado pasado no garantiza el mismo desempeño a futuro.",
            )

with st.expander("Valores pronosticados", icon=":material/table:"):
    tabla = agregado.pivot_table(index="periodo", columns="modelo", values="prediccion", observed=True)
    tabla.insert(0, "Real", agregado.drop_duplicates("periodo").set_index("periodo")["real"])
    tabla.index = tabla.index.strftime("%Y-%m")
    tabla.index.name = "Periodo"
    st.dataframe(tabla.style.format("{:,.0f}", na_rep="—"), width="stretch")
