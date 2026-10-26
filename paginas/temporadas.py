"""Temporadas: mapa de calor anio x mes (grafica 3) filtra al perfil mensual por via (grafica 4)."""

from __future__ import annotations

import streamlit as st

from src.datos import cargar_viajeros, filtrar
from src.estilo import MESES, formato_numero
from src.graficas import figura_estacionalidad, figura_perfil_mensual
from src.ui import barra_filtros, encabezado_con_vista, filtros_viajeros, indicadores, meta_datos, mosaico, nota, sin_datos

df = cargar_viajeros()
visibles = encabezado_con_vista(
    "Explorar · Demanda",
    "Temporadas",
    None,
    meta_datos(df),
    {"calor": "Mapa de calor año × mes", "perfil": "Perfil mensual por vía"},
    "temp_vis",
)

with barra_filtros("temporadas"):
    anios, tipos, vias, _ = filtros_viajeros(df, "temp")

datos = filtrar(df, anios, tipos, vias)
if datos.empty or datos["viajeros"].sum() == 0:
    sin_datos("No hay viajeros para esta combinación de filtros. Amplíe el rango de años o agregue tipos de viajero y vías.")
    st.stop()

meses_por_anio = datos.groupby("anio")["mes"].nunique()
completos = sorted(meses_por_anio[meses_por_anio == 12].index)
anio_defecto = completos[-1] if completos else int(datos["anio"].max())

# Indicadores del ultimo anio completo
ult = datos[datos["anio"] == anio_defecto].groupby("mes")["viajeros"].sum()
ref_anios = [a for a in range(2015, 2020) if a in set(datos["anio"])]
referencia = datos[datos["anio"].isin(ref_anios)].groupby("mes")["viajeros"].sum().div(len(ref_anios)) if ref_anios else None
kpis = [
    {"etiqueta": f"Mes más alto · {anio_defecto}", "valor": MESES[ult.idxmax() - 1], "contexto": f"{formato_numero(ult.max())} viajeros", "serie": ult.tolist()},
    {"etiqueta": f"Mes más bajo · {anio_defecto}", "valor": MESES[ult.idxmin() - 1], "contexto": f"{formato_numero(ult.min())} viajeros"},
    {"etiqueta": "Diferencia entre ambos", "valor": f"{ult.max() / ult.min() - 1:.0%}", "contexto": "del mes más bajo al más alto"},
]
if referencia is not None:
    kpis.append({"etiqueta": f"{anio_defecto} frente a 2015-2019", "valor": formato_numero(ult.sum()),
                 "delta": ult.sum() / referencia.sum() - 1, "delta_texto": "frente al promedio anual"})
indicadores(kpis)

if {"calor", "perfil"} <= visibles:
    col_a, col_b = st.columns([1.15, 1], gap="small")
else:
    col_a = col_b = st.container()

anios_sel: list[int] = []
if "calor" in visibles:
    with col_a, mosaico(
        "calor",
        "Viajeros por año y mes",
        "Más oscuro, más viajeros · seleccione celdas para ver ese año",
        "observado",
        "**¿Qué meses concentran a los viajeros, año con año?**\n\n"
        "Cada celda es un mes. Las columnas oscuras son las temporadas altas y la franja clara de 2020 y 2021 "
        "corresponde a la pandemia. Las celdas vacías son meses sin datos (2026 llega hasta junio). "
        "Al hacer clic en una celda, el perfil mensual muestra ese año; Shift + clic agrega otros.",
    ):
        evento = st.plotly_chart(figura_estacionalidad(datos), key="calor", on_select="rerun", selection_mode="points", width="stretch")
        puntos = evento.selection.points if evento and evento.selection else []
        anios_sel = sorted({int(p["y"]) for p in puntos if "y" in p})

if "perfil" in visibles:
    anios_ver = anios_sel or [anio_defecto]
    texto = ", ".join(map(str, anios_ver)) if len(anios_ver) <= 4 else f"{anios_ver[0]} a {anios_ver[-1]}"
    with col_b, mosaico(
        "perfil",
        "Perfil mensual por vía",
        "Viajeros por mes" + (" (promedio de los años elegidos)" if len(anios_ver) > 1 else "") + " · línea: promedio 2015-2019",
        "observado",
        "**¿Cómo se reparte el año mes a mes y qué vía explica cada temporada?**\n\n"
        "Las barras son los viajeros de cada mes por vía. La línea punteada es el promedio mensual de 2015 a 2019, "
        "en la misma escala, como referencia de un año normal antes de la pandemia. Sin selección se muestra el "
        "último año completo.",
        filtro=texto if anios_sel else None,
    ):
        detalle = datos[datos["anio"].isin(anios_ver)]
        if detalle["viajeros"].sum() == 0:
            sin_datos("Los años seleccionados no tienen viajeros con los filtros actuales.")
        else:
            st.plotly_chart(figura_perfil_mensual(datos, anios_ver, referencia), key="perfil", width="stretch")
            por_mes = detalle.groupby("mes")["viajeros"].sum().div(len(anios_ver))
            texto_obs = f"En {texto}, {MESES[por_mes.idxmax() - 1].lower()} fue el mes más alto y {MESES[por_mes.idxmin() - 1].lower()} el más bajo."
            if referencia is not None:
                comunes = por_mes.index.intersection(referencia.index)
                texto_obs += f" El volumen quedó {por_mes[comunes].sum() / referencia[comunes].sum() - 1:+.0%} frente a 2015-2019 en los mismos meses."
            nota("observado", texto_obs)
