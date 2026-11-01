"""Registro de cada ejecucion en MLflow Tracking (Laboratorio 11, ejercicio 4).

El run se crea al inicio de la ejecucion: si MLflow no responde, el pipeline se detiene antes de
leer datos y no publica una version que no se podria rastrear. Al final se registran etiquetas,
parametros, metricas y artefactos. Las metricas solo se registran si la evaluacion se completo.

MLFLOW_TRACKING_URI tiene prioridad sobre config.yaml. OBS_MLFLOW_ARTEFACTOS fija la ubicacion de
artefactos de un experimento nuevo (lo usan las pruebas); con un servidor la decide el servidor.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import yaml

# Sin reintentos largos: si el servidor no responde se sabe en segundos
os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "2")
os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "15")

from mlflow.entities import Metric, Param, RunTag  # noqa: E402
from mlflow.tracking import MlflowClient  # noqa: E402

ESTADO_MLFLOW = {"publicada": "FINISHED", "rechazada": "FINISHED", "fallida": "FAILED"}


def tracking_uri(cfg: dict) -> str:
    return os.environ.get("MLFLOW_TRACKING_URI") or cfg["mlflow"]["tracking_uri"]


def huella_config(cfg: dict) -> str:
    """SHA-256 de la configuracion sin rutas: dos maquinas con la misma configuracion dan la misma huella."""
    sin_rutas = {c: v for c, v in cfg.items() if c != "rutas" and not c.startswith("_")}
    return hashlib.sha256(yaml.safe_dump(sin_rutas, sort_keys=True, allow_unicode=True).encode()).hexdigest()


def iniciar(cfg: dict, run_id: str) -> tuple[MlflowClient, str, str]:
    """Crea el run en el experimento del destino. Devuelve el cliente, el id del run y el del experimento."""
    client = MlflowClient(tracking_uri(cfg))
    nombre = cfg["mlflow"]["experimento"]
    experimento = client.get_experiment_by_name(nombre)
    if experimento is None:
        exp_id = client.create_experiment(nombre, artifact_location=os.environ.get("OBS_MLFLOW_ARTEFACTOS"))
    else:
        exp_id = experimento.experiment_id
    run = client.create_run(exp_id, run_name=run_id, tags={"id_ejecucion": run_id, "destino": cfg["destino"]["nombre"]})
    client.log_batch(run.info.run_id, params=[Param(c, str(v)[:6000]) for c, v in parametros(cfg).items()])
    return client, run.info.run_id, exp_id


def parametros(cfg: dict) -> dict:
    """Parametros del procedimiento, periodos, reparto y umbrales de aceptacion."""
    p, per, a = cfg["procedimiento"], cfg["periodos"], cfg["aceptacion"]
    salida = {
        "destino": cfg["destino"]["nombre"],
        "variable": cfg["variable"]["nombre"],
        "unidad": cfg["variable"]["unidad"],
        "procedimiento": p["nombre"],
        "version_procedimiento": p["version"],
        "formula": p["formula"],
        "ventana_nivel": p["ventana_nivel"],
        "referencia": p["referencia"],
        "semilla": p["semilla"],
        "fuente_factor_reparto": cfg["reparto"]["fuente"],
        "umbral_mape_maximo": a["mape_maximo"],
        "umbral_mae_relativo_referencia": a["mae_relativo_referencia_maximo"],
    }
    for nombre in ("ajuste", "evaluacion", "estimacion"):
        salida[f"periodo_{nombre}_inicio"], salida[f"periodo_{nombre}_fin"] = per[nombre]
    for tipo, factor in cfg["reparto"]["factores"].items():
        salida[f"factor_{tipo}"] = factor
    return salida


def _etiquetas(m: dict) -> dict:
    t = {
        "estado": m["estado"],
        "inicio": m["inicio"],
        "fin": m.get("fin"),
        "git_commit": m["codigo"]["commit"] or "desconocido",
        "cambios_sin_commit": m["codigo"]["cambios_sin_commit"],
        "config_sha256": m["config_sha256"],
        "fuente_archivo": Path(m["fuente"]["ruta"]).name,
        "fuente_sha256": m["fuente"].get("sha256"),
        "fuente_filas": m["fuente"].get("filas"),
        "etapas_completadas": ",".join(m["etapas_completadas"]),
        "publicada": m["estado"] == "publicada",
        "error": m.get("error"),
    }
    t |= {f"calidad.{c}": e for c, e in m.get("calidad", {}).items()}
    if "aceptacion" in m:
        t["aceptacion.aprobada"] = m["aceptacion"]["aprobada"]
        t |= {f"aceptacion.{r}": v for r, v in m["aceptacion"]["reglas"].items()}
    t |= {f"monitoreo.{c}": r["estado"] for c, r in m.get("monitoreo", {}).items()}
    t |= {f"dep.{p}": v for p, v in m["dependencias"].items()}
    return {c: str(v)[:5000] for c, v in t.items() if v is not None}


def _metricas(m: dict) -> dict:
    """Solo si la evaluacion se completo: no se inventan metricas de una ejecucion detenida antes."""
    if "evaluacion" not in m["etapas_completadas"]:
        return {}
    met = m["metricas"]
    salida = {}
    for origen, prefijo in (("procedimiento", ""), ("referencia", "referencia_")):
        for nombre in ("MAE", "RMSE", "MAPE", "meses_evaluados"):
            salida[prefijo + nombre.lower()] = met[origen][nombre]
    salida["r_evaluacion"] = m["parametros"]["evaluacion"]["r"]
    if "estimacion" in m["parametros"]:
        salida["r_estimacion"] = m["parametros"]["estimacion"]["r"]
    return salida


def cerrar(client: MlflowClient, mlflow_run_id: str, manifiesto: dict, carpeta: Path) -> None:
    """Registra etiquetas, metricas, filas afectadas por control y artefactos; termina el run."""
    etiquetas = _etiquetas(manifiesto)
    metricas = _metricas(manifiesto)
    calidad = json.loads((carpeta / "calidad.json").read_text(encoding="utf-8")) if (carpeta / "calidad.json").exists() else []
    metricas |= {f"calidad_{r['control']}_filas": r["filas_afectadas"] for r in calidad}
    if manifiesto.get("monitoreo"):
        metricas["monitoreo_alertas"] = sum(r["estado"] == "alerta" for r in manifiesto["monitoreo"].values())
    ahora = int(time.time() * 1000)
    client.log_batch(
        mlflow_run_id,
        metrics=[Metric(c, float(v), ahora, 0) for c, v in metricas.items() if v is not None],
        tags=[RunTag(c, v) for c, v in etiquetas.items()],
    )
    client.log_artifacts(mlflow_run_id, str(carpeta))
    client.set_terminated(mlflow_run_id, status=ESTADO_MLFLOW.get(manifiesto["estado"], "FAILED"))
