"""Construccion de las figuras del tablero.

Separadas de las paginas para que la app y src/exportar_figuras.py (figuras del
documento de diseno) usen exactamente la misma grafica.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.estilo import (
    COLOR_HISTORIA,
    COLOR_REAL,
    COLORES_MODELO,
    COLORES_VIA,
    CUADRICULA,
    DASH_MODELO,
    EJE,
    ESCALA_DIVERGENTE,
    ESCALA_SECUENCIAL,
    MESES,
    ORDEN_VIA,
    SUPERFICIE,
    TINTA,
    TINTA_SECUNDARIA,
    TINTA_TENUE,
    aplicar_estilo,
)


def figura_evolucion(datos: pd.DataFrame, nivel: str) -> tuple[go.Figure, list[str]]:
    """Barras apiladas de viajeros por periodo y via.

    `datos` debe traer la columna `periodo`. Devuelve tambien el orden de las trazas
    (una por via), necesario para traducir `curve_number` de la seleccion a una via.
    """
    serie = datos.groupby(["periodo", "via"], observed=True)["viajeros"].sum().reset_index()
    periodos = sorted(serie["periodo"].unique())
    vias_trazas = [v for v in ORDEN_VIA if v in set(serie["via"])]

    fig = go.Figure()
    for via in vias_trazas:
        s = serie[serie["via"] == via]
        fig.add_bar(
            x=s["periodo"],
            y=s["viajeros"],
            name=via,
            marker=dict(color=COLORES_VIA[via], line=dict(color=SUPERFICIE, width=1 if nivel == "Mes" else 2)),
            hovertemplate=f"<b>%{{x}}</b><br>{via}: %{{y:,.0f}} viajeros<extra></extra>",
        )
    # Sin dragmode explicito: Streamlit solo habilita la seleccion por clic cuando el modo
    # de arrastre no es "select"/"lasso". La seleccion por caja queda en la barra de herramientas.
    fig.update_layout(barmode="stack", legend_traceorder="normal")
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=periodos, title_text=None, fixedrange=True)
    fig.update_yaxes(title_text="Viajeros", fixedrange=True)
    if nivel != "Año":
        # Con trimestres o meses, una etiqueta por año para que el eje se pueda leer
        inicios = [p for p in periodos if p.endswith(("-T1", "-01"))]
        fig.update_xaxes(tickvals=inicios, ticktext=[p[:4] for p in inicios], tickangle=0)
    aplicar_estilo(fig, alto=380)
    return fig, vias_trazas


def figura_origen(detalle: pd.DataFrame, dimension: str, top_n: int) -> tuple[go.Figure, pd.Series, pd.DataFrame]:
    """Top N categorias de `dimension` en barras horizontales apiladas por via.

    Devuelve la figura, los totales por categoria (todas, ordenadas) y el desglose por via.
    """
    desglose = detalle.groupby([dimension, "via"], observed=True)["viajeros"].sum().reset_index()
    totales = desglose.groupby(dimension, observed=True)["viajeros"].sum().sort_values(ascending=False)
    totales = totales[totales > 0]
    top = totales.head(top_n)
    orden_categorias = [str(c) for c in top.index[::-1]]  # la mayor queda arriba

    fig = go.Figure()
    for via in ORDEN_VIA:
        s = desglose[(desglose["via"] == via) & desglose[dimension].isin(top.index)]
        if s.empty:
            continue
        fig.add_bar(
            y=s[dimension].astype(str),
            x=s["viajeros"],
            name=via,
            orientation="h",
            marker=dict(color=COLORES_VIA[via], line=dict(color=SUPERFICIE, width=2)),
            hovertemplate=f"<b>%{{y}}</b><br>{via}: %{{x:,.0f}} viajeros<extra></extra>",
        )
    fig.update_layout(barmode="stack", legend_traceorder="normal")
    aplicar_estilo(fig, alto=max(320, 30 * len(top) + 80))
    # Barras horizontales: la cuadricula va en el eje de valores (x), no en el de categorias
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=orden_categorias, showgrid=False, title_text=None)
    fig.update_xaxes(title_text="Viajeros", showgrid=True, gridcolor=CUADRICULA)
    return fig, totales, desglose


def _capa_seleccion(fig: go.Figure, x: list, y: list, hover: list[str], tamano: int) -> None:
    """Plotly no permite seleccionar celdas de un mapa de calor. Se superpone un marcador
    invisible por celda: recibe el clic (y el tooltip) y, al seleccionarse, dibuja un borde
    negro alrededor de la celda elegida."""
    fig.add_scatter(
        x=x,
        y=y,
        mode="markers",
        marker=dict(symbol="square-open", size=tamano, color=TINTA, opacity=0, line=dict(width=3)),
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0)),
        customdata=hover,
        hovertemplate="%{customdata}<extra></extra>",
        showlegend=False,
    )


# ---------------------------------------------------------------- temporadas (viz 3 y 4)


def figura_estacionalidad(datos: pd.DataFrame) -> go.Figure:
    """Mapa de calor anio x mes: intensidad = viajeros. Revela temporadas y anios atipicos."""
    tabla = datos.pivot_table(index="anio", columns="mes", values="viajeros", aggfunc="sum", observed=True)
    tabla = tabla.reindex(columns=range(1, 13))
    anios = [str(a) for a in tabla.index]
    texto = tabla.map(lambda v: "sin datos" if pd.isna(v) else f"{v:,.0f} viajeros")
    fig = go.Figure(
        go.Heatmap(
            z=tabla.values,
            x=MESES,
            y=anios,
            customdata=texto.values,
            colorscale=ESCALA_SECUENCIAL,
            xgap=2,
            ygap=2,
            colorbar=dict(title=dict(text="Viajeros", side="top"), thickness=12, tickformat="~s"),
            hoverinfo="skip",
        )
    )
    xs = [m for _ in anios for m in MESES]
    ys = [a for a in anios for _ in MESES]
    hover = [f"<b>{m} {a}</b><br>{t}" for a, fila in zip(anios, texto.values) for m, t in zip(MESES, fila)]
    _capa_seleccion(fig, xs, ys, hover, tamano=22)
    aplicar_estilo(fig, alto=max(360, 24 * len(anios) + 80))
    fig.update_yaxes(type="category", range=[len(fig.data[0].y) - 0.5, -0.5], showgrid=False, title_text=None, fixedrange=True)
    fig.update_xaxes(side="top", title_text=None, fixedrange=True, range=[-0.5, len(fig.data[0].x) - 0.5])
    return fig


def figura_perfil_mensual(datos: pd.DataFrame, anios_sel: list[int], referencia: pd.Series | None) -> go.Figure:
    """Barras apiladas por via para cada mes de los anios elegidos (promedio si son varios)
    y una linea de referencia con el promedio prepandemia."""
    d = datos[datos["anio"].isin(anios_sel)]
    n_anios = max(1, d["anio"].nunique())
    serie = d.groupby(["mes", "via"], observed=True)["viajeros"].sum().div(n_anios).reset_index()
    fig = go.Figure()
    for via in ORDEN_VIA:
        s = serie[serie["via"] == via]
        if s.empty:
            continue
        fig.add_bar(
            x=[MESES[m - 1] for m in s["mes"]],
            y=s["viajeros"],
            name=via,
            marker=dict(color=COLORES_VIA[via], line=dict(color=SUPERFICIE, width=2)),
            hovertemplate=f"<b>%{{x}}</b><br>{via}: %{{y:,.0f}} viajeros<extra></extra>",
        )
    if referencia is not None and not referencia.empty:
        fig.add_scatter(
            x=[MESES[m - 1] for m in referencia.index],
            y=referencia.values,
            name="Promedio 2015-2019 (todas las vías)",
            mode="lines+markers",
            line=dict(color=TINTA, width=2, dash="dash"),
            marker=dict(size=8, color=TINTA, line=dict(color=SUPERFICIE, width=2)),
            hovertemplate="<b>%{x}</b><br>Promedio 2015-2019: %{y:,.0f}<extra></extra>",
        )
    fig.update_layout(barmode="stack", legend_traceorder="normal")
    aplicar_estilo(fig, alto=380)
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=MESES, title_text=None, fixedrange=True)
    fig.update_yaxes(title_text="Viajeros por mes" + (" (promedio)" if n_anios > 1 else ""), fixedrange=True)
    return fig


# ---------------------------------------------------------------- mercados (viz 5 y 6)


def indice_recuperacion(datos: pd.DataFrame, dimension: str, base: int, top_n: int) -> pd.DataFrame:
    """Indice anual (base = 100) comparando los mismos meses, para que un anio incompleto
    (2026 llega hasta junio) no parezca una caida. Filas: top N categorias por volumen."""
    meses_por_anio = datos.groupby("anio")["mes"].unique()
    top = datos.groupby(dimension, observed=True)["viajeros"].sum().nlargest(top_n)
    top = top[top > 0].index
    d = datos[datos[dimension].isin(top)]
    mensual = d.groupby([dimension, "anio", "mes"], observed=True)["viajeros"].sum()
    filas = {}
    for cat in top:
        if cat not in mensual.index.get_level_values(0):
            continue
        m = mensual.loc[cat]
        fila = {}
        for anio, meses in meses_por_anio.items():
            actual = m.loc[anio].reindex(meses).sum() if anio in m.index.get_level_values(0) else 0.0
            ref = m.loc[base].reindex(meses).sum() if base in m.index.get_level_values(0) else 0.0
            fila[anio] = actual / ref * 100 if ref > 0 else float("nan")
        filas[str(cat)] = fila
    return pd.DataFrame(filas).T


def figura_recuperacion(indice: pd.DataFrame, base: int) -> go.Figure:
    anios = [str(a) for a in indice.columns]
    texto = indice.map(lambda v: "" if pd.isna(v) else f"{v:.0f}")
    fig = go.Figure(
        go.Heatmap(
            z=indice.clip(upper=200).values,
            x=anios,
            y=list(indice.index),
            customdata=indice.values,
            text=texto.values,
            texttemplate="%{text}",
            textfont=dict(size=11),
            colorscale=ESCALA_DIVERGENTE,
            zmin=0,
            zmax=200,
            zmid=100,
            xgap=2,
            ygap=2,
            colorbar=dict(
                title=dict(text=f"Índice<br>{base} = 100", side="top"),
                thickness=12,
                len=0.8,
                yanchor="bottom",
                y=0,
                tickvals=[0, 50, 100, 150, 200],
                ticktext=["0", "50", "100", "150", "200+"],
            ),
            hoverinfo="skip",
        )
    )
    cats = list(indice.index)
    hover = [
        f"<b>{c} · {a}</b><br>" + ("Sin viajeros en el año base" if pd.isna(v) else f"Índice: {v:.0f} ({base} = 100)")
        for c, fila in zip(cats, indice.values) for a, v in zip(anios, fila)
    ]
    _capa_seleccion(fig, [a for _ in cats for a in anios], [c for c in cats for _ in anios], hover, tamano=24)
    aplicar_estilo(fig, alto=max(320, 34 * len(indice) + 90))
    fig.update_yaxes(type="category", range=[len(fig.data[0].y) - 0.5, -0.5], showgrid=False, title_text=None, fixedrange=True)
    fig.update_xaxes(type="category", side="top", title_text=None, fixedrange=True, range=[-0.5, len(fig.data[0].x) - 0.5])
    return fig


def figura_treemap(detalle: pd.DataFrame, profundidad: int) -> go.Figure:
    """Jerarquia region -> pais. Clic en un rectangulo para acercar; clic en el borde superior para volver."""
    base = detalle.groupby(["region", "pais"], observed=True)["viajeros"].sum().reset_index()
    base = base[base["viajeros"] > 0]
    regiones = base.groupby("region", observed=True)["viajeros"].sum()
    total = regiones.sum()
    ids = ["Todas"] + [f"r/{r}" for r in regiones.index] + [f"p/{r}/{p}" for r, p in zip(base["region"], base["pais"])]
    labels = ["Todos los orígenes"] + [str(r) for r in regiones.index] + [str(p) for p in base["pais"]]
    parents = [""] + ["Todas"] * len(regiones) + [f"r/{r}" for r in base["region"]]
    values = [total] + list(regiones.values) + list(base["viajeros"])
    fig = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            maxdepth=profundidad + 1,
            marker=dict(colors=values, colorscale=ESCALA_SECUENCIAL, line=dict(color=SUPERFICIE, width=2), showscale=False),
            texttemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percentRoot:.1%}",
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} viajeros<br>%{percentParent:.1%} de %{parent}<br>%{percentRoot:.1%} del total<extra></extra>",
            pathbar=dict(visible=True, thickness=22),
            tiling=dict(pad=2),
        )
    )
    aplicar_estilo(fig, alto=480)
    fig.update_layout(margin=dict(l=4, r=4, t=28, b=4))
    return fig


# ---------------------------------------------------------------- modelos (viz 7 a 11)


def _etiqueta_fecha(fechas: pd.Series, nivel: str) -> list[str]:
    if nivel == "Año":
        return [str(f.year) for f in fechas]
    if nivel == "Trimestre":
        return [f"T{(f.month - 1) // 3 + 1} {f.year}" for f in fechas]
    return [f"{MESES[f.month - 1]} {f.year}" for f in fechas]


def figura_pronostico(
    historia: pd.DataFrame, pron: pd.DataFrame, modelos: list[str], nivel: str, mostrar_intervalo: bool
) -> go.Figure:
    """Valor real (negro) frente a lo que cada modelo pronostico para el periodo de prueba."""
    fig = go.Figure()
    corte = pron["fecha"].min()
    if not historia.empty:
        fig.add_scatter(
            x=historia["fecha"],
            y=historia["valor"],
            name="Real (entrenamiento)",
            mode="lines",
            line=dict(color=COLOR_HISTORIA, width=1.5),
            customdata=_etiqueta_fecha(historia["fecha"], nivel),
            hovertemplate="<b>%{customdata}</b><br>Real: %{y:,.0f}<extra></extra>",
        )
    real = pron.drop_duplicates("periodo").sort_values("periodo")
    for modelo in modelos:
        s = pron[pron["modelo"] == modelo].sort_values("periodo")
        if s.empty:
            continue
        color = COLORES_MODELO[modelo]
        if mostrar_intervalo and s["limite_inferior"].notna().any():
            r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
            fig.add_scatter(
                x=list(s["periodo"]) + list(s["periodo"][::-1]),
                y=list(s["limite_superior"]) + list(s["limite_inferior"][::-1]),
                fill="toself",
                fillcolor=f"rgba({r},{g},{b},0.14)",
                line=dict(width=0),
                name=f"Rango probable 95 % · {modelo}",
                hoverinfo="skip",
                showlegend=True,
            )
        fig.add_scatter(
            x=s["periodo"],
            y=s["prediccion"],
            name=modelo,
            mode="lines",
            line=dict(color=color, width=2, dash=DASH_MODELO[modelo]),
            customdata=_etiqueta_fecha(s["periodo"], nivel),
            hovertemplate=f"<b>%{{customdata}}</b><br>{modelo}: %{{y:,.0f}}<extra></extra>",
        )
    fig.add_scatter(
        x=real["periodo"],
        y=real["real"],
        name="Real (prueba)",
        mode="lines+markers",
        line=dict(color=COLOR_REAL, width=2.5),
        marker=dict(size=7 if nivel == "Mes" else 10, color=COLOR_REAL, line=dict(color=SUPERFICIE, width=2)),
        customdata=_etiqueta_fecha(real["periodo"], nivel),
        hovertemplate="<b>%{customdata}</b><br>Real: %{y:,.0f}<extra></extra>",
    )
    fig.add_vline(x=corte, line=dict(color=TINTA_TENUE, width=1, dash="dot"))
    fig.add_annotation(
        x=corte, y=1, yref="paper", text="Inicio del periodo de prueba", showarrow=False, xanchor="left", yanchor="top",
        xshift=6, font=dict(color=TINTA_SECUNDARIA, size=12),
    )
    aplicar_estilo(fig, alto=460)
    fig.update_layout(hovermode="closest", legend_traceorder="normal")
    fig.update_xaxes(title_text=None, tickformat="%Y")
    fig.update_yaxes(title_text="Viajeros" + ("" if nivel == "Mes" else f" por {nivel.lower()}"), rangemode="tozero")
    return fig


def figura_error_modelos(metricas: pd.DataFrame, metrica: str, etiqueta_metrica: str) -> go.Figure:
    """Barras horizontales: un modelo por barra, el de menor error arriba."""
    m = metricas.dropna(subset=[metrica]).sort_values(metrica, ascending=False)
    sufijo = " %" if metrica == "MAPE" else ""
    fig = go.Figure(
        go.Bar(
            y=m["modelo"].astype(str),
            x=m[metrica],
            orientation="h",
            marker=dict(color=[COLORES_MODELO[str(x)] for x in m["modelo"]], line=dict(color=SUPERFICIE, width=2)),
            text=[f"{v:,.1f}{sufijo}" if metrica == "MAPE" else f"{v:,.0f}" for v in m[metrica]],
            textposition="outside",
            textfont=dict(color=TINTA_SECUNDARIA),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>" + etiqueta_metrica + ": %{x:,.1f}<extra></extra>",
        )
    )
    aplicar_estilo(fig, alto=max(240, 52 * len(m) + 60))
    fig.update_yaxes(type="category", showgrid=False, title_text=None, fixedrange=True)
    fig.update_xaxes(title_text=etiqueta_metrica, showgrid=True, gridcolor=CUADRICULA, rangemode="tozero", fixedrange=True)
    fig.update_layout(showlegend=False, margin=dict(l=8, r=60, t=8, b=8))
    return fig


def figura_mapa_errores(tabla: pd.DataFrame, metrica: str, etiqueta_metrica: str) -> go.Figure:
    """Serie x modelo. Mas oscuro = mas error. Las celdas sin evaluacion muestran 'sin dato'."""
    texto = tabla.map(lambda v: "sin dato" if pd.isna(v) else (f"{v:.1f} %" if metrica == "MAPE" else f"{v:,.0f}"))
    fig = go.Figure(
        go.Heatmap(
            z=tabla.values,
            x=list(tabla.columns),
            y=list(tabla.index),
            text=texto.values,
            texttemplate="%{text}",
            textfont=dict(size=12),
            colorscale=ESCALA_SECUENCIAL,
            xgap=3,
            ygap=3,
            colorbar=dict(title=dict(text=metrica, side="top"), thickness=12),
            hoverinfo="skip",
        )
    )
    filas, cols = list(tabla.index), [str(c) for c in tabla.columns]
    hover = [f"<b>{f}</b><br>{c}: {t}" for f, fila in zip(filas, texto.values) for c, t in zip(cols, fila)]
    _capa_seleccion(fig, [c for _ in filas for c in cols], [f for f in filas for _ in cols], hover, tamano=34)
    aplicar_estilo(fig, alto=max(320, 46 * len(tabla) + 80))
    fig.update_yaxes(type="category", range=[len(fig.data[0].y) - 0.5, -0.5], showgrid=False, title_text=None, fixedrange=True)
    fig.update_xaxes(type="category", side="top", title_text=None, fixedrange=True, range=[-0.5, len(fig.data[0].x) - 0.5])
    return fig


def figura_error_horizonte(por_anio: pd.DataFrame, metrica: str, etiqueta_metrica: str) -> go.Figure:
    """Error de cada modelo por anio del periodo de prueba: muestra si empeora al alejarse del corte."""
    fig = go.Figure()
    for modelo in por_anio["modelo"].cat.categories if hasattr(por_anio["modelo"], "cat") else por_anio["modelo"].unique():
        s = por_anio[por_anio["modelo"] == modelo].dropna(subset=[metrica])
        if s.empty:
            continue
        fig.add_scatter(
            x=s["anio"].astype(str),
            y=s[metrica],
            name=str(modelo),
            mode="lines+markers",
            line=dict(color=COLORES_MODELO[str(modelo)], width=2, dash=DASH_MODELO[str(modelo)]),
            marker=dict(size=9, color=COLORES_MODELO[str(modelo)], line=dict(color=SUPERFICIE, width=2)),
            hovertemplate=f"<b>{modelo}</b> · %{{x}}<br>{etiqueta_metrica}: %{{y:,.1f}}<extra></extra>",
        )
    aplicar_estilo(fig, alto=400)
    fig.update_xaxes(type="category", title_text="Año del periodo de prueba", fixedrange=True)
    fig.update_yaxes(title_text=etiqueta_metrica, rangemode="tozero", fixedrange=True)
    return fig


def figura_tuneo(tuneo: pd.DataFrame, elegido: str) -> go.Figure:
    """Error de validacion de cada configuracion LSTM probada en el Laboratorio 2."""
    t = tuneo.sort_values("val_RMSE")
    colores = [COLORES_MODELO["LSTM"] if m == elegido else EJE for m in t["modelo"]]
    desc = [
        f"Ventana {int(r.look_back)} meses · {int(r.unidades_1)}"
        + (f"+{int(r.unidades_2)}" if pd.notna(r.unidades_2) else "")
        + f" unidades · dropout {r.dropout} · tasa de aprendizaje {r.learning_rate}"
        + f"<br>Mejor época {int(r.mejor_epoca)} de {int(r.epocas_ejecutadas)}"
        for r in t.itertuples()
    ]
    fig = go.Figure(
        go.Bar(
            x=t["modelo"],
            y=t["val_RMSE"],
            marker=dict(color=colores, line=dict(color=SUPERFICIE, width=2)),
            customdata=desc,
            text=[f"{v:,.0f}" for v in t["val_RMSE"]],
            textposition="outside",
            textfont=dict(color=TINTA_SECUNDARIA),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>RMSE de validación: %{y:,.0f}<br>%{customdata}<extra></extra>",
        )
    )
    aplicar_estilo(fig, alto=340)
    fig.update_xaxes(type="category", title_text="Configuración probada", fixedrange=True)
    fig.update_yaxes(title_text="Error de validación (RMSE)", rangemode="tozero", fixedrange=True)
    fig.update_layout(showlegend=False, margin=dict(l=8, r=8, t=28, b=8))
    return fig
