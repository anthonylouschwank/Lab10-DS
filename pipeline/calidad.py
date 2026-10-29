"""Controles automaticos de calidad (Laboratorio 11, ejercicio 3).

Cada control termina en "ok", "advertencia" o "critico". Un resultado critico detiene el pipeline
antes de ajustar el procedimiento, asi que el tablero sigue leyendo la ultima version aprobada.
Ningun control rellena con cero un mes sin informacion.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import procedimiento as proc

OK, ADVERTENCIA, CRITICO = "ok", "advertencia", "critico"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# control -> (que se verifica, cuando genera advertencia, cuando detiene la ejecucion)
CRITERIOS = {
    "a_columnas_tipos": (
        "Que existan las columnas de la fuente y que las indispensables (anio, mes, tipo, viajeros) tengan un tipo compatible.",
        "Falta una columna descriptiva que no interviene en la estimacion.",
        "Falta una columna indispensable o tiene valores que no se pueden convertir a su tipo (texto en un conteo, mes con decimales).",
    ),
    "b_fechas_cobertura": (
        "Que anio y mes formen fechas validas y que cada mes del ajuste y la evaluacion tenga registros de los tipos usados.",
        "El nombre del mes no coincide con su codigo, o falta un mes fuera del periodo necesario.",
        "Hay meses fuera de 1-12, anios anteriores al minimo o fechas futuras, o un mes necesario no tiene informacion.",
    ),
    "c_unicidad": (
        "Que no se repita la clave anio-mes-via-frontera-pais-agrupacion-tipo, que es la granularidad mensual de la fuente.",
        "Hay claves repetidas solo en tipos que no se usan para estimar (Viajero, Cruceristas).",
        "Hay claves repetidas en los tipos usados: esos visitantes se contarian dos veces.",
    ),
    "d_faltantes": (
        "Que los faltantes esten solo donde se permiten.",
        "Faltan valores en columnas descriptivas o en conteos de tipos que no se usan (ausencia permitida).",
        "Falta anio, mes o tipo, o falta el conteo de un tipo usado para estimar (impide estimar).",
    ),
    "e_valores_denominadores": (
        "Que los conteos sean finitos y no negativos y que el denominador de la razon de nivel r sea mayor que cero.",
        "Hay meses evaluados con valor observado cero (se excluyen del MAPE) o valores invalidos en tipos no usados.",
        "Hay conteos negativos o no finitos en los tipos usados, o el denominador de r es cero o no se puede calcular.",
    ),
    "f_regla_metodologica": (
        "Que la serie mensual sume solo turistas y excursionistas de la fuente mensual, sin columnas diarias ni filas de total, "
        "y que concilie con la suma directa de la fuente.",
        "El factor de reparto todavia es un supuesto sin fuente documentada.",
        "Se usan tipos que no son visitantes, la fuente trae granularidad diaria o filas de total, el factor esta fuera de [0, 1] "
        "o la serie no concilia con la fuente.",
    ),
}


@dataclass
class Resultado:
    control: str
    estado: str
    detalle: str
    filas_afectadas: int = 0


class ControlCritico(Exception):
    """Fallo un control critico: no se ajusta ni se publica."""


def _estado(critico: bool, advertencia: bool) -> str:
    return CRITICO if critico else ADVERTENCIA if advertencia else OK


def _sin_acentos(texto: str) -> str:
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().strip().lower()


def _columnas_tipos(raw: pd.DataFrame, cfg: dict) -> tuple[Resultado, pd.DataFrame | None]:
    columnas: dict = cfg["fuente"]["columnas"]
    indispensables = cfg["fuente"]["indispensables"]
    faltan = [o for o in columnas if o not in raw.columns]
    faltan_ind = [o for o in faltan if columnas[o] in indispensables]
    if faltan_ind:
        return Resultado("a_columnas_tipos", CRITICO, f"Faltan columnas indispensables: {faltan_ind}"), None

    df = raw[[o for o in columnas if o in raw.columns]].rename(columns=columnas)
    problemas, afectadas = [], 0
    for col in ("anio", "mes", "viajeros"):
        num = pd.to_numeric(df[col], errors="coerce")
        malos = df[col].notna() & num.isna()
        if col != "viajeros":
            malos |= num.notna() & (num % 1 != 0)
        if malos.any():
            problemas.append(f"{col}: {int(malos.sum())} valores incompatibles")
            afectadas += int(malos.sum())
        df[col] = num
    if pd.api.types.is_numeric_dtype(df["tipo"]):
        problemas.append("tipo: es numerico, se esperaba texto")
        afectadas += len(df)
    else:
        df["tipo"] = df["tipo"].astype("string").str.strip()

    if problemas:
        return Resultado("a_columnas_tipos", CRITICO, "; ".join(problemas), afectadas), None
    detalle = f"Columnas descriptivas ausentes: {faltan}" if faltan else "Columnas y tipos completos"
    return Resultado("a_columnas_tipos", _estado(False, bool(faltan)), detalle), df


def _fechas_validas(df: pd.DataFrame, cfg: dict) -> pd.Series:
    hoy = pd.Period(date.today(), freq="M")
    ok = df["anio"].notna() & df["mes"].notna() & df["mes"].between(1, 12) & (df["anio"] >= cfg["calidad"]["anio_minimo"])
    ok &= (df["anio"] * 12 + df["mes"]) <= (hoy.year * 12 + hoy.month)
    return ok


def _fechas_cobertura(df: pd.DataFrame, cfg: dict) -> Resultado:
    fechas_ok = _fechas_validas(df, cfg)
    invalidas = df["anio"].notna() & df["mes"].notna() & ~fechas_ok
    problemas, avisos = [], []
    if invalidas.any():
        problemas.append(f"{int(invalidas.sum())} filas con fecha invalida o futura")

    if "mes_nombre" in df:
        esperado = df["mes"].where(fechas_ok).map(lambda m: MESES[int(m) - 1] if pd.notna(m) else None)
        distinto = fechas_ok & df["mes_nombre"].notna() & (df["mes_nombre"].astype(str).str.strip() != esperado)
        if distinto.any():
            avisos.append(f"{int(distinto.sum())} filas con nombre de mes distinto a su codigo")

    validas = df[fechas_ok & df["viajeros"].notna()]
    necesarios = proc.periodos_necesarios(cfg)
    for tipo in proc.tipos_usados(cfg):
        d = validas[validas["tipo"] == tipo]
        presentes = set(proc.periodos_de(d["anio"], d["mes"]))
        sin_info = [str(p) for p in necesarios if p not in presentes]
        if sin_info:
            problemas.append(f"{tipo} sin informacion en meses necesarios: {sin_info}")
        if presentes:
            fuera = [str(p) for p in pd.period_range(min(presentes), max(presentes), freq="M") if p not in presentes and p not in necesarios]
            if fuera:
                avisos.append(f"{tipo} sin informacion fuera del periodo necesario: {fuera}")
    detalle = "; ".join(problemas + avisos) or f"Fechas validas y cobertura completa de {necesarios[0]} a {necesarios[-1]}"
    return Resultado("b_fechas_cobertura", _estado(bool(problemas), bool(avisos)), detalle, int(invalidas.sum()))


def _unicidad(df: pd.DataFrame, cfg: dict) -> Resultado:
    clave = [c for c in cfg["fuente"]["clave"] if c in df]
    repetidas = df.duplicated(clave, keep=False)
    en_usados = repetidas & df["tipo"].isin(proc.tipos_usados(cfg))
    detalle = (
        f"{int(repetidas.sum())} filas con clave repetida ({int(en_usados.sum())} en tipos usados); clave {clave}"
        if repetidas.any()
        else f"Sin claves repetidas; clave {clave}"
    )
    return Resultado("c_unicidad", _estado(en_usados.any(), repetidas.any()), detalle, int(repetidas.sum()))


def _faltantes(df: pd.DataFrame, cfg: dict) -> Resultado:
    usados = df["tipo"].isin(proc.tipos_usados(cfg))
    sin_clave = df[["anio", "mes", "tipo"]].isna().any(axis=1)
    sin_conteo_usado = df["viajeros"].isna() & usados
    sin_conteo_otro = df["viajeros"].isna() & ~usados & df["tipo"].notna()
    descriptivas = [c for c in df.columns if c not in cfg["fuente"]["indispensables"]]
    faltan_desc = {c: int(n) for c, n in df[descriptivas].isna().sum().items() if n}
    partes = []
    if sin_clave.any():
        partes.append(f"{int(sin_clave.sum())} filas sin anio, mes o tipo")
    if sin_conteo_usado.any():
        partes.append(f"{int(sin_conteo_usado.sum())} conteos faltantes en tipos usados")
    if sin_conteo_otro.any():
        partes.append(f"{int(sin_conteo_otro.sum())} conteos faltantes en tipos no usados (permitido)")
    if faltan_desc:
        partes.append(f"faltantes en columnas descriptivas (permitido): {faltan_desc}")
    critico = sin_clave.any() or sin_conteo_usado.any()
    return Resultado(
        "d_faltantes",
        _estado(critico, sin_conteo_otro.any() or bool(faltan_desc)),
        "; ".join(partes) or "Sin faltantes",
        int((sin_clave | sin_conteo_usado).sum()),
    )


def _valores_denominadores(df: pd.DataFrame, cfg: dict) -> Resultado:
    usados = df["tipo"].isin(proc.tipos_usados(cfg))
    invalidos = df["viajeros"].notna() & (~np.isfinite(df["viajeros"]) | (df["viajeros"] < 0))
    problemas, avisos = [], []
    if (invalidos & usados).any():
        problemas.append(f"{int((invalidos & usados).sum())} conteos negativos o no finitos en tipos usados")
    if (invalidos & ~usados).any():
        avisos.append(f"{int((invalidos & ~usados).sum())} conteos negativos o no finitos en tipos no usados")

    validos = df[_fechas_validas(df, cfg) & df["viajeros"].notna() & ~invalidos]
    y = proc.construir_serie(validos, cfg)["destino"]
    k = cfg["procedimiento"]["ventana_nivel"]
    for nombre, origen in proc.origenes(cfg).items():
        _, den = proc.razon_nivel(y, origen, k)
        if not (np.isfinite(den) and den > 0):
            problemas.append(f"denominador de r para {nombre} (origen {origen}) es {den}")
    evaluados = y.reindex(proc.rango(cfg["periodos"]["evaluacion"]))
    ceros = [str(p) for p, v in evaluados.items() if v == 0]
    if ceros:
        avisos.append(f"meses evaluados con valor observado cero, excluidos del MAPE: {ceros}")
    detalle = "; ".join(problemas + avisos) or "Conteos finitos y no negativos; denominadores de r mayores que cero"
    return Resultado("e_valores_denominadores", _estado(bool(problemas), bool(avisos)), detalle, int(invalidos.sum()))


def _regla_metodologica(raw: pd.DataFrame, df: pd.DataFrame, cfg: dict) -> Resultado:
    problemas, avisos = [], []
    no_visitante = [t for t in proc.tipos_usados(cfg) if t not in cfg["fuente"]["tipos_visitante"]]
    if no_visitante:
        problemas.append(f"se suman tipos que no son visitantes: {no_visitante}")
    diarias = [c for c in raw.columns if _sin_acentos(c) in {"dia", "fecha", "day", "date"}]
    if diarias:
        problemas.append(f"la fuente trae columnas de granularidad diaria {diarias}; la serie debe venir de la fuente mensual")
    totales = df["tipo"].dropna().map(_sin_acentos).str.contains("total")
    if totales.any():
        problemas.append(f"{int(totales.sum())} filas de total en tipo (doble conteo)")
    nuevos = sorted(set(df["tipo"].dropna()) - set(cfg["fuente"]["tipos_conocidos"]))
    if nuevos:
        avisos.append(f"tipos de viajero no reconocidos (no se usan): {nuevos}")
    fuera = {t: f for t, f in proc.factores(cfg).items() if not 0 <= f <= 1}
    if fuera:
        problemas.append(f"factores de reparto fuera de [0, 1]: {fuera}")
    if str(cfg["reparto"].get("fuente", "")).upper().startswith("SUPUESTO"):
        avisos.append("el factor de reparto es un supuesto sin fuente documentada")

    # Conciliacion: la serie del procedimiento contra una suma directa de la fuente mensual
    validos = df[_fechas_validas(df, cfg) & df["viajeros"].notna()]
    serie = proc.construir_serie(validos, cfg)["destino"]
    peso = validos["tipo"].map(proc.factores(cfg)).fillna(0)
    directa = (validos["viajeros"] * peso).groupby([validos["anio"].astype(int), validos["mes"].astype(int)]).sum()
    directa.index = proc.periodos_de(directa.index.get_level_values(0), directa.index.get_level_values(1))
    comunes = serie.dropna().index.intersection(directa.index)
    diferencia = float((serie[comunes] - directa[comunes]).abs().max()) if len(comunes) else 0.0
    if diferencia > cfg["calidad"]["tolerancia_conciliacion"]:
        problemas.append(f"la serie no concilia con la fuente mensual (diferencia maxima {diferencia:.4f})")

    detalle = "; ".join(problemas + avisos) or "Serie mensual de visitantes conciliada con la fuente mensual"
    return Resultado("f_regla_metodologica", _estado(bool(problemas), bool(avisos)), detalle)


def validar(raw: pd.DataFrame, cfg: dict) -> tuple[list[Resultado], pd.DataFrame | None]:
    """Corre los seis controles. Devuelve los resultados y los datos tipados (None si (a) es critico)."""
    res_a, df = _columnas_tipos(raw, cfg)
    if df is None:
        return [res_a], None
    return [
        res_a,
        _fechas_cobertura(df, cfg),
        _unicidad(df, cfg),
        _faltantes(df, cfg),
        _valores_denominadores(df, cfg),
        _regla_metodologica(raw, df, cfg),
    ], df


def hay_criticos(resultados: list[Resultado]) -> bool:
    return any(r.estado == CRITICO for r in resultados)


def escribir_reporte(resultados: list[Resultado], carpeta: Path) -> None:
    """Reporte en JSON (para MLflow y pruebas) y en Markdown (para leerlo)."""
    filas = []
    for r in resultados:
        verifica, advierte, detiene = CRITERIOS[r.control]
        filas.append(asdict(r) | {"verifica": verifica, "advertencia_si": advierte, "detiene_si": detiene})
    (carpeta / "calidad.json").write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
    lineas = ["# Reporte de controles de calidad", "", "| Control | Estado | Detalle |", "|---|---|---|"]
    lineas += [f"| {r.control} | {r.estado} | {r.detalle} |" for r in resultados]
    if len(resultados) < len(CRITERIOS):
        lineas += ["", "Los demas controles no se ejecutaron porque fallo el control de columnas y tipos."]
    (carpeta / "calidad.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
