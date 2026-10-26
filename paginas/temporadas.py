"""Temporadas: mapa de calor anio x mes (grafica 3) enlazado con el perfil mensual por via (grafica 4)."""

from __future__ import annotations

import streamlit as st

from src.datos import cargar_viajeros, filtrar
from src.estilo import MESES, formato_numero
from src.graficas import figura_estacionalidad, figura_perfil_mensual
from src.ui import barra_filtros, encabezado_pagina, filtros_viajeros, hallazgo, selector_graficas, sin_datos, tarjeta_grafica

encabezado_pagina(
    "Explorar los datos · 2 de 3",
    "Temporadas altas y bajas",
    "En qué meses se concentra la demanda y cómo ha cambiado ese patrón. Al hacer clic en el mapa de calor, "
    "la gráfica de abajo muestra el detalle mensual de los años elegidos.",
)

df = cargar_viajeros()
with barra_filtros("temporadas"):
    anios, tipos, vias, _ = filtros_viajeros(df, "temp")
    visibles = selector_graficas({"calor": "3 · Mapa de calor año × mes", "perfil": "4 · Perfil mensual por vía"}, key="temp_vis")

datos = filtrar(df, anios, tipos, vias)
if datos.empty or datos["viajeros"].sum() == 0:
    sin_datos("No hay viajeros para esta combinación de filtros. Amplíe el rango de años o agregue tipos de viajero y vías.")
    st.stop()

# Ultimo anio completo: valor por defecto de la grafica 4
meses_por_anio = datos.groupby("anio")["mes"].nunique()
completos = sorted(meses_por_anio[meses_por_anio == 12].index)
anio_defecto = completos[-1] if completos else int(datos["anio"].max())

anios_sel: list[int] = []
meses_sel: list[str] = []
if "calor" in visibles:
    with tarjeta_grafica(
        3,
        "¿Qué meses concentran a los viajeros, año con año?",
        "observado",
        "Sirve para planificar personal, promoción y capacidad según la temporada, y para detectar años atípicos.",
        "Cada celda es un mes: cuanto más oscuro el azul, más viajeros llegaron. Las columnas oscuras señalan las "
        "temporadas altas; la franja clara de 2020 y 2021, el efecto de la pandemia. Las celdas vacías son meses sin "
        "datos (2026 llega hasta junio).\n\n"
        "**Para profundizar:** haga clic en una celda y la gráfica 4 mostrará ese año mes a mes. Con Shift puede "
        "agregar más años; doble clic restablece la selección.",
        "<b>Clic en una celda</b> para ver ese año en la gráfica 4 · Shift + clic para comparar varios",
    ):
        evento = st.plotly_chart(figura_estacionalidad(datos), key="calor", on_select="rerun", selection_mode="points", width="stretch")
        puntos = evento.selection.points if evento and evento.selection else []
        anios_sel = sorted({int(p["y"]) for p in puntos if "y" in p})
        meses_sel = [m for m in MESES if m in {p.get("x") for p in puntos}]

if "perfil" in visibles:
    anios_ver = anios_sel or [anio_defecto]
    texto = ", ".join(map(str, anios_ver)) if len(anios_ver) <= 5 else f"{len(anios_ver)} años ({anios_ver[0]}-{anios_ver[-1]})"
    with tarjeta_grafica(
        4,
        f"¿Cómo se reparte {texto} mes a mes?",
        "observado",
        "Sirve para comparar un año con lo que era normal antes de 2020 y ver qué vía explica cada temporada.",
        "Las barras muestran los viajeros de cada mes por vía de ingreso; si se eligen varios años, el promedio. "
        "La línea punteada es el promedio mensual de 2015-2019, la referencia previa a la pandemia, en la misma escala.",
    ):
        if not anios_sel:
            st.caption(f"Se muestra {anio_defecto}, el último año completo. Elija otros años en la gráfica 3.")
        ref_anios = [a for a in range(2015, 2020) if a in set(datos["anio"])]
        referencia = datos[datos["anio"].isin(ref_anios)].groupby("mes")["viajeros"].sum().div(len(ref_anios)) if ref_anios else None
        detalle = datos[datos["anio"].isin(anios_ver)]
        if detalle["viajeros"].sum() == 0:
            sin_datos("Los años seleccionados no tienen viajeros con los filtros actuales.")
        else:
            st.plotly_chart(figura_perfil_mensual(datos, anios_ver, referencia), key="perfil", width="stretch")
            if referencia is None:
                st.caption("La referencia 2015-2019 no aparece porque el rango de años filtrado no incluye esos años.")

            por_mes = detalle.groupby("mes")["viajeros"].sum().div(len(anios_ver))
            alto, bajo = por_mes.idxmax(), por_mes.idxmin()
            texto_obs = (
                f"El mes con más viajeros fue **{MESES[alto - 1]}** ({formato_numero(por_mes.max())}) y el de menos, "
                f"**{MESES[bajo - 1]}** ({formato_numero(por_mes.min())})."
            )
            if referencia is not None:
                comunes = por_mes.index.intersection(referencia.index)
                cambio = por_mes[comunes].sum() / referencia[comunes].sum() - 1
                texto_obs += f" En los meses con datos, el volumen queda **{cambio:+.0%}** frente al promedio 2015-2019."
            if meses_sel:
                texto_obs += f" Meses marcados en el mapa: {', '.join(meses_sel)}."
            c1, c2 = st.columns(2)
            with c1:
                hallazgo("observado", texto_obs)
            with c2:
                hallazgo(
                    "interpretacion",
                    "Un mes alto puede coincidir con vacaciones, eventos o cambios en el registro; estos datos no "
                    "permiten saber cuál de esas causas actuó.",
                )
