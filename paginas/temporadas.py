"""Temporadas: mapa de calor anio x mes (viz 3) enlazado con el perfil mensual por via (viz 4)."""

from __future__ import annotations

import streamlit as st

from src.datos import cargar_viajeros, filtrar
from src.estilo import MESES, formato_numero
from src.graficas import figura_estacionalidad, figura_perfil_mensual
from src.ui import encabezado_grafica, etiqueta, filtros_viajeros, nota_fuente, selector_graficas, sin_datos

st.title("Temporadas altas y bajas")
st.markdown(
    "¿En qué meses se concentra la demanda y cómo cambió ese patrón con los años? "
    "Haz clic en una o varias celdas del mapa de calor para ver el detalle mensual por vía de esos años."
)
nota_fuente()

df = cargar_viajeros()
anios, tipos, vias = filtros_viajeros(df, key="temp")
datos = filtrar(df, anios, tipos, vias)
if datos.empty or datos["viajeros"].sum() == 0:
    sin_datos("No hay viajeros para la combinación de filtros elegida. Amplía el rango de años o agrega tipos de viajero y vías.")
    st.stop()

visibles = selector_graficas({"calor": "3. Mapa de calor año × mes", "perfil": "4. Perfil mensual por vía"}, key="temp_vis")

# Anios completos disponibles, para elegir uno por defecto en la grafica 4
meses_por_anio = datos.groupby("anio")["mes"].nunique()
completos = sorted(meses_por_anio[meses_por_anio == 12].index)
anio_defecto = completos[-1] if completos else int(datos["anio"].max())

anios_sel: list[int] = []
meses_sel: list[str] = []
if "calor" in visibles:
    encabezado_grafica(
        3,
        "¿Qué meses concentran a los viajeros, año con año?",
        "observado",
        "cada celda es un mes; mientras más oscuro el azul, más viajeros llegaron. Las celdas vacías son meses sin datos (2026 llega hasta junio).",
        "planificar personal, promoción y capacidad para las temporadas altas, y detectar años atípicos (2020-2021).",
    )
    st.caption("**Haz clic en una celda** para ver ese año en la gráfica 4. Mantén Shift para agregar más años. Doble clic limpia la selección.")
    evento = st.plotly_chart(
        figura_estacionalidad(datos), key="calor", on_select="rerun", selection_mode="points", use_container_width=True
    )
    puntos = evento.selection.points if evento and evento.selection else []
    anios_sel = sorted({int(p["y"]) for p in puntos if "y" in p})
    meses_sel = [m for m in MESES if m in {p.get("x") for p in puntos}]

if "perfil" in visibles:
    anios_ver = anios_sel or [anio_defecto]
    texto = ", ".join(map(str, anios_ver)) if len(anios_ver) <= 5 else f"{len(anios_ver)} años ({anios_ver[0]}-{anios_ver[-1]})"
    encabezado_grafica(
        4,
        f"¿Cómo se reparte el año {texto} mes a mes?",
        "observado",
        "viajeros de cada mes por vía de ingreso (promedio si eliges varios años) y, en línea punteada, el promedio mensual 2015-2019 como referencia previa a la pandemia.",
        "comparar un año contra lo que era normal antes de 2020 y ver qué vía explica cada temporada.",
    )
    if not anios_sel:
        st.caption(f"Mostrando {anio_defecto}, el último año completo. Selecciona celdas en la gráfica 3 para cambiarlo.")
    ref_anios = [a for a in range(2015, 2020) if a in set(datos["anio"])]
    referencia = (
        datos[datos["anio"].isin(ref_anios)].groupby("mes")["viajeros"].sum().div(len(ref_anios)) if ref_anios else None
    )
    detalle = datos[datos["anio"].isin(anios_ver)]
    if detalle["viajeros"].sum() == 0:
        sin_datos("Los años seleccionados no tienen viajeros con los filtros actuales.")
    else:
        st.plotly_chart(figura_perfil_mensual(datos, anios_ver, referencia), key="perfil", use_container_width=True)
        if referencia is None:
            st.caption("La línea de referencia 2015-2019 no aparece porque el rango de años filtrado no incluye esos años.")

        # Resumen textual de lo observado en la seleccion
        por_mes = detalle.groupby("mes")["viajeros"].sum().div(len(anios_ver))
        alto, bajo = por_mes.idxmax(), por_mes.idxmin()
        etiqueta("observado")
        lineas = [
            f"- Mes con más viajeros: **{MESES[alto - 1]}** ({formato_numero(por_mes.max())}); "
            f"mes con menos: **{MESES[bajo - 1]}** ({formato_numero(por_mes.min())})."
        ]
        if referencia is not None:
            meses_comunes = por_mes.index.intersection(referencia.index)
            cambio = por_mes[meses_comunes].sum() / referencia[meses_comunes].sum() - 1
            lineas.append(
                f"- En los meses con datos, el volumen es **{cambio:+.0%}** respecto al promedio 2015-2019 de esos mismos meses."
            )
        if meses_sel:
            lineas.append(f"- Meses marcados en el mapa: {', '.join(meses_sel)}.")
        st.markdown("\n".join(lineas))
        st.caption(
            "Esto describe lo ocurrido; no explica sus causas. Un mes alto puede coincidir con vacaciones, eventos o "
            "cambios de registro, pero estos datos no permiten atribuirlo a uno de ellos."
        )
