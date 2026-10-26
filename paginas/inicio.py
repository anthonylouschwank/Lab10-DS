"""Inicio: portada ejecutiva con indicadores, hallazgos y acceso a cada seccion."""

import streamlit as st

from src.datos import TIPOS_COMPARABLES, cargar_viajeros
from src.estilo import formato_numero
from src.modelos import cargar_pronosticos, tabla_metricas
from src.ui import encabezado_pagina, hallazgo, indicadores

# Nombres cortos para los textos de las tarjetas
NOMBRE_CORTO = {"América Del Centro": "Centroamérica", "América Del Norte": "Norteamérica"}

df = cargar_viajeros()
d = df[df["tipo"].isin(TIPOS_COMPARABLES)]
ultimo = d["fecha"].max()
anio = ultimo.year - 1 if ultimo.month < 12 else ultimo.year
por_anio = d.groupby("anio")["viajeros"].sum()
cambio_2019 = por_anio[anio] / por_anio[2019] - 1
caida_2020 = por_anio[2020] / por_anio[2019] - 1
por_via = d[d["anio"] == anio].groupby("via", observed=True)["viajeros"].sum()
por_region = d[d["anio"] == anio].groupby("region", observed=True)["viajeros"].sum()
region = por_region.idxmax()

met = tabla_metricas(cargar_pronosticos(), ["serie", "modelo"])
total = met[(met["serie"] == "Total mensual") & (met["modelo"] != "Referencia ingenua")].sort_values("MAPE").iloc[0]
ref_total = met[(met["serie"] == "Total mensual") & (met["modelo"] == "Referencia ingenua")]["MAPE"].iloc[0]

encabezado_pagina(
    "Observatorio de Turismo Sostenible · Guatemala",
    "Llegadas internacionales: dónde estamos y qué esperar",
    f"Tablero para la dirección del sector turístico. Reúne {ultimo.year - 2009 + 1} años de registros migratorios "
    "para entender la demanda, sus temporadas y sus mercados, y para saber cuánto confiar en los pronósticos disponibles.",
)

signo = "neg" if cambio_2019 < 0 else "pos"
indicadores(
    [
        (f"Viajeros en {anio}", formato_numero(por_anio[anio]), f'<span class="{signo}">{cambio_2019:+.0%}</span> frente a 2019'),
        (f"Vía {por_via.idxmax().lower()} · {anio}", f"{por_via.max() / por_via.sum():.0%}", "de las llegadas; es la vía principal"),
        (f"{NOMBRE_CORTO.get(region, region)} · {anio}", f"{por_region.max() / por_region.sum():.0%}", "de las llegadas; es la región principal"),
        (f"Mejor pronóstico · {total['modelo']}", f"{total['MAPE']:.0f} %", f"error promedio del total, frente a {ref_total:.0f} % de la referencia"),
    ]
)
st.caption(f"Turistas y excursionistas. Datos hasta {ultimo:%m/%Y}; {anio} es el último año completo.")

c1, c2 = st.columns(2, gap="medium")
with c1:
    hallazgo(
        "observado",
        f"En {anio} llegaron **{formato_numero(por_anio[anio])} viajeros**, {abs(cambio_2019):.0%} "
        f"{'más' if cambio_2019 >= 0 else 'menos'} que en 2019. En 2020 la cifra había caído {abs(caida_2020):.0%}. "
        f"La vía {por_via.idxmax().lower()} y los visitantes de {NOMBRE_CORTO.get(region, region)} siguen concentrando la demanda.\n\n"
        "La fuente cambió su forma de registro en 2021 y en 2023, así que parte de la diferencia frente a 2019 puede "
        "deberse a ese cambio y no solo a la demanda.",
    )
with c2:
    hallazgo(
        "estimacion",
        f"Para el total mensual, **{total['modelo']}** se desvió en promedio {formato_numero(total['MAE'])} viajeros por mes "
        f"({total['MAPE']:.0f} % del valor real) entre abril de 2021 y junio de 2026. Ningún modelo gana en todas las series: "
        "en las terrestres el error supera el 65 %, y esos pronósticos deben usarse con cautela.",
    )

st.html('<div class="op-eyebrow" style="margin-top:1.6rem">Por dónde empezar</div>')
SECCIONES = [
    (
        "paginas/explorar.py", "Explorar los datos", "Qué ocurrió",
        "Evolución de la demanda, temporadas y mercados de origen, con gráficas que se filtran entre sí.",
        ["¿Cómo evolucionan las llegadas y por qué vía?", "¿Qué meses concentran la demanda?", "¿Qué mercados ya superan 2019?"],
        ":material/bar_chart:",
    ),
    (
        "paginas/modelos.py", "Pronósticos", "Qué se espera",
        "Lo que pronosticó cada modelo frente a lo que realmente ocurrió, mes a mes.",
        ["¿Qué pronosticó cada modelo?", "¿Cuál se equivocó menos en un periodo dado?"],
        ":material/trending_up:",
    ),
    (
        "paginas/comparar.py", "Comparar modelos", "Cuánto confiar",
        "El error de cada modelo en cada serie y su evolución a lo largo del horizonte.",
        ["¿Qué modelo conviene en cada serie?", "¿Hasta qué horizonte es confiable?"],
        ":material/leaderboard:",
    ),
]
cols = st.columns(3, gap="medium")
for i, (col, (pagina, titulo, clave, desc, preguntas, icono)) in enumerate(zip(cols, SECCIONES)):
    with col, st.container(border=True, key=f"nav-{i}"):
        lista = "".join(f"<li>{q}</li>" for q in preguntas)
        st.html(
            f'<div class="op-nav-k">{clave}</div><div class="op-nav-t">{titulo}</div>'
            f'<div class="op-nav-d">{desc}</div><ul class="op-nav-q">{lista}</ul>'
        )
        st.page_link(pagina, label=f"Ir a {titulo.lower()}", icon=icono)

st.html('<div class="op-eyebrow" style="margin-top:1.6rem">Cómo leer el tablero</div>')
st.markdown(
    "Cada gráfica se titula con la pregunta que responde y lleva una etiqueta que indica si muestra un "
    ":blue-badge[Dato observado], una :gray-badge[Interpretación] o una :violet-badge[Estimación de modelo]. "
    "El botón **Cómo leerla** explica cada gráfica en detalle, y en **Gráficas visibles** puede ocultar las que no "
    "necesite. Los términos técnicos están en **Glosario y limitaciones**."
)
