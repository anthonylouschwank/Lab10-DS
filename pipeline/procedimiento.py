"""Procedimiento de estimacion: estacional con ajuste de nivel y factor de reparto.

    destino(t) = sum_tipo factor_tipo * llegadas_tipo(t)
    y_hat(o + h) = y(o + h - 12) * r(o)        (si o + h - 12 > o se usa la propia estimacion)
    r(o) = sum(y[o-k+1 .. o]) / sum(y[o-k+1-12 .. o-12])

o es el ultimo mes observado antes de los meses estimados y k la ventana de nivel. Solo usa
valores hasta o, asi que la evaluacion no ve informacion futura. No tiene componentes aleatorios.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def periodo(texto: str) -> pd.Period:
    return pd.Period(texto, freq="M")


def periodos_de(anio, mes) -> pd.PeriodIndex:
    return pd.PeriodIndex.from_fields(year=np.asarray(anio, dtype=int), month=np.asarray(mes, dtype=int), freq="M")


def rango(par: list[str]) -> pd.PeriodIndex:
    return pd.period_range(periodo(par[0]), periodo(par[1]), freq="M")


def factores(cfg: dict) -> dict[str, float]:
    return {t: float(f) for t, f in cfg["reparto"]["factores"].items()}


def tipos_usados(cfg: dict) -> list[str]:
    return [t for t, f in factores(cfg).items() if f > 0]


def periodos_necesarios(cfg: dict) -> pd.PeriodIndex:
    """Meses que deben tener informacion: del inicio del ajuste al fin de la evaluacion."""
    return pd.period_range(periodo(cfg["periodos"]["ajuste"][0]), periodo(cfg["periodos"]["evaluacion"][1]), freq="M")


def origenes(cfg: dict) -> dict[str, pd.Period]:
    """Ultimo mes observado para evaluar (antes de la evaluacion) y para estimar (fin de la evaluacion)."""
    return {
        "evaluacion": periodo(cfg["periodos"]["evaluacion"][0]) - 1,
        "estimacion": periodo(cfg["periodos"]["evaluacion"][1]),
    }


def construir_serie(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Serie mensual por tipo usado y del destino. Un mes sin registros queda NaN, nunca cero."""
    usados = tipos_usados(cfg)
    d = df[df["tipo"].isin(usados)]
    tabla = d.assign(periodo=periodos_de(d["anio"], d["mes"])).groupby(["periodo", "tipo"])["viajeros"].sum(min_count=1).unstack("tipo")
    tabla = tabla.reindex(columns=usados)
    if len(tabla):
        tabla = tabla.reindex(pd.period_range(tabla.index.min(), tabla.index.max(), freq="M"))
    tabla.index.name = "periodo"
    peso = pd.Series(factores(cfg))[usados]
    tabla["destino"] = (tabla[usados] * peso).sum(axis=1, min_count=len(usados))
    return tabla


def razon_nivel(y: pd.Series, origen: pd.Period, k: int) -> tuple[float, float]:
    """Numerador y denominador de r(o): ultimos k meses frente a los mismos meses un ano antes."""
    num = y.reindex(pd.period_range(origen - k + 1, origen, freq="M")).sum(min_count=k)
    den = y.reindex(pd.period_range(origen - k + 1 - 12, origen - 12, freq="M")).sum(min_count=k)
    return float(num), float(den)


def estimar(y: pd.Series, origen: pd.Period, periodos: pd.PeriodIndex, k: int) -> tuple[pd.Series, dict]:
    y = y.loc[:origen]
    num, den = razon_nivel(y, origen, k)
    if not (np.isfinite(num) and np.isfinite(den) and den > 0):
        raise ValueError(f"No se puede calcular r en {origen}: numerador {num}, denominador {den}")
    r = num / den
    est: dict[pd.Period, float] = {}
    for t in periodos:
        base = y.get(t - 12, np.nan) if t - 12 <= origen else est.get(t - 12, np.nan)
        est[t] = base * r
    parametros = {"origen": str(origen), "ventana_nivel": k, "numerador": num, "denominador": den, "r": r}
    return pd.Series(est, name="estimado"), parametros


def referencia(y: pd.Series, origen: pd.Period, periodos: pd.PeriodIndex) -> pd.Series:
    """Referencia sencilla: repetir el ultimo valor observado."""
    return pd.Series(float(y.loc[origen]), index=periodos, name="referencia")


def metricas(observado: pd.Series, estimado: pd.Series) -> dict:
    """MAE, RMSE y MAPE. El MAPE excluye los meses observados iguales a cero (se reporta cuantos)."""
    m = observado.notna() & estimado.notna()
    obs, est = observado[m], estimado[m]
    error = obs - est
    nz = obs != 0
    return {
        "MAE": float(error.abs().mean()) if m.any() else np.nan,
        "RMSE": float(np.sqrt((error**2).mean())) if m.any() else np.nan,
        "MAPE": float((error[nz] / obs[nz]).abs().mean() * 100) if nz.any() else np.nan,
        "meses_evaluados": int(m.sum()),
        "meses_cero_excluidos_mape": int((~nz).sum()),
    }
