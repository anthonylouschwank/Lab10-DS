"""Estimaciones del destino (Laboratorio 11): muestra la version aprobada del pipeline.

Solo lee salidas/vigente.json y los archivos de esa version; aqui no se ajusta ni se recalcula nada.
Los detalles tecnicos (parametros, ejecuciones) quedan en MLflow y en docs/lab11.md.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.estilo import formato_numero
from src.estimaciones import cargar_version, leer_vigente
from src.graficas import figura_estimaciones, figura_validacion
from src.ui import MESES_CORTOS, barra_filtros, encabezado_con_vista, encabezado_pagina, indicadores, mosaico, nota


def mes(periodo: str) -> str:
    p = pd.Period(periodo, freq="M")
    return f"{MESES_CORTOS[p.month - 1]} {p.year}"


info, carpeta = leer_vigente()
if info is None:
    encabezado_pagina("Estimaciones", "Estimaciones del destino")
    st.warning(
        "Las estimaciones no estan disponibles: todavia no hay una version aprobada del pipeline. "
        "Se mostraran aqui en cuanto una ejecucion pase los controles de calidad y la regla de aceptacion.",
        icon=":material/hourglass_empty:",
    )
    st.stop()

v = cargar_version(str(carpeta), info["id_ejecucion"])
est, obs, ev, met, cfg = v["estimaciones"], v["observados"], v["evaluacion"], v["metricas"], v["config"]
destino, unidad = est["destino"].iloc[0], est["unidad"].iloc[0]
generado = pd.Timestamp(est["fecha_generacion"].iloc[0])
eval_ini, eval_fin = met["meses_evaluados"]
proc_m, ref_m = met["procedimiento"], met["referencia"]
factor = cfg["reparto"]["factores"].get("Turista", 0)
supuesto = str(cfg["reparto"].get("fuente", "")).upper().startswith("SUPUESTO")

visibles = encabezado_con_vista(
    "Estimaciones",
    f"Visitantes internacionales · {destino}",
    None,
    f"Actualizado <b>{generado.day} {MESES_CORTOS[generado.month - 1]} {generado.year}</b><br>"
    f"Estimado <b>{mes(est['periodo'].iloc[0])} a {mes(est['periodo'].iloc[-1])}</b>",
    {"serie": "Observado y estimado", "validacion": "Validacion", "tabla": "Tabla de estimaciones"},
    "est_vis",
)

if info.get("restaurada"):
    st.info(
        f"Se muestra una version anterior, restaurada el {info['publicado'][:10]}. La version mas reciente se conserva y puede volver a publicarse.",
        icon=":material/history:",
    )

indicadores(
    [
        {"etiqueta": f"Estimado para {mes(est['periodo'].iloc[0])}", "valor": formato_numero(est["valor"].iloc[0]),
         "contexto": f"{unidad}; primer mes sin dato observado"},
        {"etiqueta": f"Total estimado {mes(est['periodo'].iloc[0])} a {mes(est['periodo'].iloc[-1])}", "valor": formato_numero(est["valor"].sum()),
         "contexto": f"{len(est)} meses", "serie": est["valor"].tolist()},
        {"etiqueta": "Error de validacion", "valor": f"{proc_m['MAPE']:.1f} %",
         "contexto": f"referencia sencilla: {ref_m['MAPE']:.1f} %"},
        {"etiqueta": "Error promedio en visitantes", "valor": formato_numero(proc_m["MAE"]),
         "contexto": f"por mes, {mes(eval_ini)} a {mes(eval_fin)}"},
    ]
)

st.warning(
    f"**Como leer estas cifras.** La base de migracion no cuenta visitantes por destino. La serie de {destino} "
    f"atribuye al destino el {factor * 100:.0f} % de los turistas que ingresan al pais"
    + (" (un supuesto, pendiente del factor oficial)" if supuesto else "")
    + ", asi que el nivel es aproximado; la tendencia y la estacionalidad son las del pais. "
    "Las estimaciones son valores esperados, no cifras oficiales, y se reemplazan cuando llega el dato observado.",
    icon=":material/info:",
)

with barra_filtros("estimaciones"):
    anio_min, anio_max = int(obs["fecha"].dt.year.min()), int(obs["fecha"].dt.year.max())
    desde = st.slider("Mostrar observados desde", anio_min, anio_max, max(anio_min, anio_max - 3), key="est_desde")

if "serie" in visibles:
    with mosaico(
        "est-serie",
        "Visitantes observados y estimados",
        f"{unidad} · {destino}",
        "estimacion",
        "**Que muestra.** La linea negra continua son los meses observados. La linea violeta discontinua, con puntos "
        "huecos, son las estimaciones de los meses que todavia no tienen dato; el fondo violeta marca ese tramo.\n\n"
        "**Como se estima.** Cada mes repite el mismo mes del ano anterior, ajustado por cuanto crecieron o bajaron "
        "los ultimos 12 meses frente a los 12 previos.",
    ):
        st.plotly_chart(figura_estimaciones(obs[obs["fecha"].dt.year >= desde], est, unidad), key="est_serie", width="stretch")

if "validacion" in visibles and ev is not None:
    with mosaico(
        "est-validacion",
        "Que tan cerca quedo el procedimiento",
        f"Validacion con {mes(eval_ini)} a {mes(eval_fin)} ocultos",
        "estimacion",
        "**Como se valido.** Se ocultaron los meses observados de "
        f"{mes(eval_ini)} a {mes(eval_fin)} y se estimaron solo con los datos anteriores, como si no existieran. "
        "Luego se compararon con lo que realmente ocurrio. La referencia sencilla repite el ultimo mes observado.",
    ):
        st.plotly_chart(figura_validacion(ev), key="est_validacion", width="stretch")
        mejor = proc_m["MAPE"] <= ref_m["MAPE"]
        nota(
            "estimacion",
            f"En los {proc_m['meses_evaluados']} meses ocultos el procedimiento se desvio en promedio {proc_m['MAPE']:.1f} % "
            f"({formato_numero(proc_m['MAE'])} {unidad}); repetir el ultimo mes observado se desvia {ref_m['MAPE']:.1f} %. "
            + ("El procedimiento queda mas cerca que la referencia." if mejor else "La referencia queda mas cerca en estos meses."),
        )

if v["monitoreo"] and any(r["estado"] == "alerta" for r in v["monitoreo"].values()):
    nota("interpretacion", "Esta version tiene alertas de monitoreo pendientes de revision tecnica. Una alerta pide revisar "
         "los datos o la variacion de las cifras; por si sola no indica que las estimaciones sean incorrectas.")

if "tabla" in visibles:
    with st.expander("Valores estimados", icon=":material/table:", expanded=False):
        tabla = pd.DataFrame({
            "Mes": [mes(p) for p in est["periodo"]],
            f"Valor estimado ({unidad})": est["valor"].round(0),
            "Tipo de valor": est["tipo_valor"].str.capitalize(),
        })
        st.dataframe(tabla.style.format({f"Valor estimado ({unidad})": "{:,.0f}"}), width="stretch", hide_index=True)
        st.caption(f"Version {info['id_ejecucion']} · procedimiento {est['version_procedimiento'].iloc[0]} · generada {generado:%Y-%m-%d %H:%M}")
