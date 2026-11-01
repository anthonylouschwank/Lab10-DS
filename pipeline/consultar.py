"""Consulta las ejecuciones registradas en MLflow y deja la evidencia en archivos (ejercicio 4.2 y 4.3).

Uso:
    python -m pipeline.consultar                 # escribe evidencia/mlflow_ejecuciones.csv y .md

- Lista todas las ejecuciones del experimento con su estado, commit, huellas y metricas.
- Identifica las fallidas y su causa (sin metricas si se detuvieron antes de la evaluacion).
- Compara las dos ejecuciones completas mas recientes con la misma fuente y configuracion:
  descarga sus estimaciones de MLflow y mide la diferencia maxima contra la tolerancia.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import pandas as pd
from mlflow.tracking import MlflowClient

from pipeline import seguimiento
from pipeline.configuracion import CONFIG_DEFECTO, ROOT, cargar

COLUMNAS = {
    "tags.mlflow.runName": "id_ejecucion",
    "run_id": "mlflow_run_id",
    "status": "estado_mlflow",
    "tags.estado": "estado",
    "tags.inicio": "inicio",
    "tags.git_commit": "git_commit",
    "tags.fuente_sha256": "fuente_sha256",
    "tags.config_sha256": "config_sha256",
    "tags.etapas_completadas": "etapas_completadas",
    "metrics.mae": "mae",
    "metrics.rmse": "rmse",
    "metrics.mape": "mape",
    "metrics.referencia_mae": "referencia_mae",
    "metrics.referencia_mape": "referencia_mape",
    "tags.aceptacion.aprobada": "aprobada",
    "tags.error": "error",
}


def ejecuciones(cfg: dict) -> pd.DataFrame:
    """Todas las ejecuciones del experimento del destino, de la mas antigua a la mas reciente."""
    client = MlflowClient(seguimiento.tracking_uri(cfg))
    experimento = client.get_experiment_by_name(cfg["mlflow"]["experimento"])
    if experimento is None:
        return pd.DataFrame(columns=list(COLUMNAS.values()))
    runs = client.search_runs([experimento.experiment_id], order_by=["attributes.start_time ASC"], max_results=5000)
    filas = []
    for r in runs:
        plano = {"run_id": r.info.run_id, "status": r.info.status}
        plano |= {f"tags.{c}": v for c, v in r.data.tags.items()}
        plano |= {f"metrics.{c}": v for c, v in r.data.metrics.items()}
        filas.append({nuevo: plano.get(viejo) for viejo, nuevo in COLUMNAS.items()})
    return pd.DataFrame(filas, columns=list(COLUMNAS.values()))


def comparar_reproducibilidad(cfg: dict, tabla: pd.DataFrame) -> dict | None:
    """Diferencia entre las estimaciones de las dos ultimas ejecuciones completas con los mismos datos y configuracion."""
    completas = tabla[tabla["estado"].isin(["publicada", "rechazada"])]
    for i in range(len(completas) - 1, 0, -1):
        b, previas = completas.iloc[i], completas.iloc[:i]
        iguales = previas[(previas["fuente_sha256"] == b["fuente_sha256"]) & (previas["config_sha256"] == b["config_sha256"])]
        if len(iguales):
            a = iguales.iloc[-1]
            break
    else:
        return None
    client = MlflowClient(seguimiento.tracking_uri(cfg))
    with tempfile.TemporaryDirectory() as tmp:
        ea = pd.read_parquet(client.download_artifacts(a["mlflow_run_id"], "estimaciones.parquet", f"{tmp}/a"))
        eb = pd.read_parquet(client.download_artifacts(b["mlflow_run_id"], "estimaciones.parquet", f"{tmp}/b"))
    unidas = ea.merge(eb, on="periodo", suffixes=("_a", "_b"))
    diferencia = float((unidas["valor_a"] - unidas["valor_b"]).abs().max())
    tolerancia = cfg["reproducibilidad"]["tolerancia"]
    return {
        "ejecucion_a": a["id_ejecucion"],
        "ejecucion_b": b["id_ejecucion"],
        "periodos_comparados": len(unidas),
        "mismos_periodos": len(unidas) == len(ea) == len(eb),
        "diferencia_maxima": diferencia,
        "diferencia_mae": abs(float(a["mae"]) - float(b["mae"])),
        "tolerancia": tolerancia,
        "equivalentes": len(unidas) == len(ea) == len(eb) and diferencia <= tolerancia,
    }


def _corto(valor) -> str:
    return str(valor)[:10] if isinstance(valor, str) else ""


def escribir_evidencia(cfg: dict, carpeta: Path) -> tuple[pd.DataFrame, dict | None]:
    tabla = ejecuciones(cfg)
    repro = comparar_reproducibilidad(cfg, tabla)
    carpeta.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(carpeta / "mlflow_ejecuciones.csv", index=False)

    lineas = [
        "# Consulta de ejecuciones en MLflow",
        "",
        f"Experimento `{cfg['mlflow']['experimento']}` en `{seguimiento.tracking_uri(cfg)}`. "
        f"{len(tabla)} ejecuciones; tabla completa en `mlflow_ejecuciones.csv`.",
        "",
        "| Ejecucion | Estado | MLflow | Commit | Fuente | MAE | MAPE % | Ref. MAE | Causa del fallo |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in tabla.iterrows():
        mae = "" if pd.isna(r["mae"]) else f"{r['mae']:,.0f}"
        mape = "" if pd.isna(r["mape"]) else f"{r['mape']:.2f}"
        ref = "" if pd.isna(r["referencia_mae"]) else f"{r['referencia_mae']:,.0f}"
        error = r["error"].replace("|", "/")[:160] if isinstance(r["error"], str) else ""
        lineas.append(f"| {r['id_ejecucion']} | {r['estado']} | {r['estado_mlflow']} | {_corto(r['git_commit'])} | {_corto(r['fuente_sha256'])} | {mae} | {mape} | {ref} | {error} |")

    fallidas = tabla[tabla["estado"] == "fallida"]
    lineas += ["", "## Ejecuciones fallidas", ""]
    if fallidas.empty:
        lineas.append("No hay ejecuciones fallidas.")
    for _, r in fallidas.iterrows():
        con_metricas = "con metricas de evaluacion" if pd.notna(r["mae"]) else "sin metricas (se detuvo antes de evaluar)"
        lineas.append(f"- {r['id_ejecucion']}: {r['error']}. Etapas completadas: {r['etapas_completadas'] or 'ninguna'}; {con_metricas}.")

    lineas += ["", "## Reproducibilidad", ""]
    if repro is None:
        lineas.append("Todavia no hay dos ejecuciones completas con la misma fuente y configuracion.")
    else:
        veredicto = "equivalentes" if repro["equivalentes"] else "NO equivalentes"
        lineas.append(
            f"{repro['ejecucion_a']} y {repro['ejecucion_b']} (misma huella de fuente y de configuracion): "
            f"{repro['periodos_comparados']} periodos comparados, diferencia maxima {repro['diferencia_maxima']:.3g} visitantes, "
            f"diferencia de MAE {repro['diferencia_mae']:.3g}, tolerancia {repro['tolerancia']:g}. Resultado: {veredicto}."
        )
    (carpeta / "mlflow_consulta.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return tabla, repro


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consulta de ejecuciones en MLflow")
    parser.add_argument("--config", default=str(CONFIG_DEFECTO))
    parser.add_argument("--salida", default=str(ROOT / "evidencia"))
    args = parser.parse_args(argv)
    tabla, repro = escribir_evidencia(cargar(args.config), Path(args.salida))
    print(tabla[["id_ejecucion", "estado", "estado_mlflow", "mae", "mape", "error"]].to_string(index=False))
    if repro:
        print(f"Reproducibilidad: {repro}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
