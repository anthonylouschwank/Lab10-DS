"""Inicio: resumen de la demanda, tendencia mensual, lectura principal y acceso a cada seccion."""

import streamlit as st

from src.datos import TIPOS_COMPARABLES, cargar_viajeros
from src.estilo import formato_numero
from src.graficas import figura_tendencia
from src.modelos import cargar_pronosticos, tabla_metricas
from src.ui import encabezado_pagina, indicadores, meta_datos, mosaico, nota

NOMBRE_CORTO = {"América Del Centro": "Centroamérica", "América Del Norte": "Norteamérica"}

df = cargar_viajeros()
d = df[df["tipo"].isin(TIPOS_COMPARABLES)]
ultimo = d["fecha"].max()
anio = ultimo.year - 1 if ultimo.month < 12 else ultimo.year
por_anio = d.groupby("anio")["viajeros"].sum()
completos = por_anio.loc[:anio]
por_via = d[d["anio"] == anio].groupby("via", observed=True)["viajeros"].sum()
por_region = d[d["anio"] == anio].groupby("region", observed=True)["viajeros"].sum()
region = por_region.idxmax()
serie_via = d[d["via"] == por_via.idxmax()].groupby("anio")["viajeros"].sum().loc[:anio]
serie_region = d[d["region"] == region].groupby("anio")["viajeros"].sum().loc[:anio]

met = tabla_metricas(cargar_pronosticos(), ["serie", "modelo"])
total = met[(met["serie"] == "Total mensual") & (met["modelo"] != "Referencia ingenua")].sort_values("MAPE").iloc[0]
ref_total = met[(met["serie"] == "Total mensual") & (met["modelo"] == "Referencia ingenua")]["MAPE"].iloc[0]

encabezado_pagina("Observatorio de Turismo Sostenible", "Resumen", None, meta_datos(df))

indicadores(
    [
        {"etiqueta": f"Viajeros {anio}", "valor": formato_numero(por_anio[anio]), "delta": por_anio[anio] / por_anio[anio - 1] - 1,
         "delta_texto": f"frente a {anio - 1}", "serie": completos.tolist()},
        {"etiqueta": f"Frente a 2019", "valor": f"{por_anio[anio] / por_anio[2019]:.0%}", "contexto": "del volumen previo a la pandemia",
         "serie": completos.loc[2015:].tolist()},
        {"etiqueta": f"Vía {por_via.idxmax().lower()} · {anio}", "valor": f"{por_via.max() / por_via.sum():.0%}", "contexto": "de las llegadas", "serie": serie_via.tolist()},
        {"etiqueta": f"{NOMBRE_CORTO.get(region, region)} · {anio}", "valor": f"{por_region.max() / por_region.sum():.0%}", "contexto": "de las llegadas", "serie": serie_region.tolist()},
    ]
)

mensual = d.groupby("fecha")["viajeros"].sum()
col_a, col_b = st.columns([1.8, 1], gap="small")
with col_a, mosaico(
    "tendencia",
    "Llegadas mensuales",
    "Turistas y excursionistas, todas las vías · línea oscura: promedio móvil de 12 meses",
    "observado",
    "**¿Cómo ha evolucionado la demanda?**\n\n"
    "El área gris son las llegadas de cada mes; la línea oscura promedia los doce meses anteriores, lo que elimina "
    "la estacionalidad y deja ver la tendencia. Arrastre sobre la gráfica para acercarse a un periodo y haga doble clic para volver.",
):
    st.plotly_chart(figura_tendencia(mensual), key="tendencia", width="stretch")

with col_b, st.container(key="tile-lectura"):
    st.html('<div class="ot-tt">Lectura principal</div><div class="ot-ts">Lo observado y lo que estiman los modelos</div>')
    nota(
        "observado",
        f"En {anio} llegaron {formato_numero(por_anio[anio])} viajeros, el {por_anio[anio] / por_anio[2019]:.0%} de 2019. "
        f"La vía {por_via.idxmax().lower()} y los visitantes de {NOMBRE_CORTO.get(region, region)} concentran la demanda.",
    )
    nota(
        "interpretacion",
        "La fuente cambió su registro en 2021 y en 2023; parte de la distancia frente a 2019 puede venir de ese "
        "cambio y no solo de la demanda.",
    )
    nota(
        "estimacion",
        f"Para el total mensual, {total['modelo']} es el pronóstico más preciso: {total['MAPE']:.0f} % de error promedio "
        f"frente a {ref_total:.0f} % de la referencia ingenua. En las series terrestres ningún modelo baja de 65 %.",
    )

ACCESOS = [
    ("paginas/explorar.py", "Evolución y origen", "Volumen por vía de ingreso y origen de los viajeros, con filtro cruzado entre gráficas.", ":material/bar_chart:"),
    ("paginas/temporadas.py", "Temporadas", "Estacionalidad año con año y perfil mensual frente a 2015-2019.", ":material/calendar_month:"),
    ("paginas/mercados.py", "Mercados y recuperación", "Índice de recuperación frente a 2019 y peso de cada región y país.", ":material/public:"),
    ("paginas/modelos.py", "Pronósticos", "Pronóstico de cada modelo frente a lo observado, mes a mes.", ":material/trending_up:"),
    ("paginas/comparar.py", "Comparar modelos", "Error de cada modelo por serie y por año del horizonte.", ":material/leaderboard:"),
]
cols = st.columns(len(ACCESOS), gap="small")
for i, (col, (pagina, titulo, desc, icono)) in enumerate(zip(cols, ACCESOS)):
    with col, st.container(key=f"acceso-{i}"):
        st.html(f'<div class="ot-acc-t">{titulo}</div><div class="ot-acc-d">{desc}</div>')
        st.page_link(pagina, label="Abrir", icon=icono)
