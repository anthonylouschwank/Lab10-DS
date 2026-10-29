"""Orquesta el pipeline: lectura -> validacion -> preparacion -> ajuste -> evaluacion ->
estimacion -> almacenamiento -> publicacion.

Uso:
    python -m pipeline                      # config/config.yaml
    python -m pipeline --config otra.yaml --fuente /datos/base.xlsx

Cada ejecucion escribe todo en salidas/ejecuciones/<id>/. Solo una version aprobada se copia a
salidas/versiones/<id>/ y se apunta desde salidas/vigente.json, que es lo que lee el tablero.
Si algo falla, vigente.json no se toca y el tablero sigue con la ultima version aprobada.

Codigo de salida: 0 publicada, 2 completa pero rechazada por la regla de aceptacion, 1 fallida.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import random
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from pipeline import calidad
from pipeline import procedimiento as proc
from pipeline.configuracion import CONFIG_DEFECTO, ROOT, cargar

DEPENDENCIAS = ["pandas", "numpy", "pyarrow", "openpyxl", "PyYAML"]
ETAPAS = ["lectura", "validacion", "preparacion", "ajuste", "evaluacion", "estimacion", "almacenamiento", "publicacion"]


def _huella(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _commit() -> dict:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()

    try:
        return {"commit": git("rev-parse", "HEAD"), "cambios_sin_commit": bool(git("status", "--porcelain"))}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "cambios_sin_commit": None}


def _versiones() -> dict:
    v = {"python": platform.python_version()}
    for paquete in DEPENDENCIAS:
        try:
            v[paquete] = metadata.version(paquete)
        except metadata.PackageNotFoundError:
            v[paquete] = None
    return v


def leer_fuente(cfg: dict) -> pd.DataFrame:
    fuente: Path = cfg["rutas"]["fuente"]
    if not fuente.exists():
        raise FileNotFoundError(f"No existe la fuente {fuente} (configure rutas.fuente u OBS_FUENTE)")
    if fuente.suffix in (".xlsx", ".xls"):
        return pd.read_excel(fuente, sheet_name=cfg["fuente"]["hoja"])
    if fuente.suffix == ".parquet":
        return pd.read_parquet(fuente)
    return pd.read_csv(fuente)


def _logger(carpeta: Path, run_id: str) -> logging.Logger:
    log = logging.getLogger(f"pipeline.{run_id}")
    log.setLevel(logging.INFO)
    log.propagate = False
    formato = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    for handler in (logging.FileHandler(carpeta / "registro.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)):
        handler.setFormatter(formato)
        log.addHandler(handler)
    return log


def _regla_aceptacion(resultados, estimaciones: pd.DataFrame, cfg: dict, met: dict, met_ref: dict) -> dict:
    a = cfg["aceptacion"]
    esperados = len(proc.rango(cfg["periodos"]["estimacion"]))
    valores = estimaciones["valor"]
    reglas = {
        "controles_sin_criticos": not calidad.hay_criticos(resultados),
        "salidas_completas": len(estimaciones) == esperados and bool(np.isfinite(valores).all() and (valores >= 0).all()),
        "mape_bajo_umbral": bool(np.isfinite(met["MAPE"]) and met["MAPE"] <= a["mape_maximo"]),
        "mae_frente_a_referencia": bool(
            np.isfinite(met["MAE"]) and np.isfinite(met_ref["MAE"]) and met["MAE"] <= a["mae_relativo_referencia_maximo"] * met_ref["MAE"]
        ),
    }
    return {"reglas": reglas, "aprobada": all(reglas.values()), "umbrales": a}


def _publicar(carpeta: Path, salidas: Path, run_id: str) -> Path:
    """Copia la ejecucion a versiones/ y cambia vigente.json de forma atomica."""
    destino = salidas / "versiones" / run_id
    shutil.copytree(carpeta, destino, ignore=shutil.ignore_patterns("registro.log", "datos_preparados.parquet"))
    vigente = salidas / "vigente.json"
    anterior = json.loads(vigente.read_text(encoding="utf-8")) if vigente.exists() else None
    nuevo = {
        "id_ejecucion": run_id,
        "ruta": f"versiones/{run_id}",
        "publicado": datetime.now().isoformat(timespec="seconds"),
        "anterior": anterior["id_ejecucion"] if anterior else None,
    }
    tmp = vigente.with_suffix(".tmp")
    tmp.write_text(json.dumps(nuevo, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, vigente)
    return destino


def ejecutar(cfg: dict) -> dict:
    inicio = datetime.now()
    run_id = f"{inicio:%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    salidas: Path = cfg["rutas"]["salidas"]
    carpeta = salidas / "ejecuciones" / run_id
    carpeta.mkdir(parents=True)
    log = _logger(carpeta, run_id)

    semilla = cfg["procedimiento"]["semilla"]
    random.seed(semilla)
    np.random.seed(semilla)

    destino, unidad = cfg["destino"]["nombre"], cfg["variable"]["unidad"]
    version_proc = cfg["procedimiento"]["version"]
    k = cfg["procedimiento"]["ventana_nivel"]
    manifiesto = {
        "id_ejecucion": run_id,
        "inicio": inicio.isoformat(timespec="seconds"),
        "codigo": _commit(),
        "dependencias": _versiones(),
        "configuracion": cfg["_archivo"],
        "fuente": {"ruta": str(cfg["rutas"]["fuente"])},
        "periodos": cfg["periodos"],
        "procedimiento": cfg["procedimiento"],
        "reparto": cfg["reparto"],
        "etapas_completadas": [],
        "estado": "en_curso",
    }
    copia_cfg = {c: v for c, v in cfg.items() if not c.startswith("_")} | {"rutas": {c: str(v) for c, v in cfg["rutas"].items()}}
    (carpeta / "config.yaml").write_text(yaml.safe_dump(copia_cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def completar(etapa: str) -> None:
        manifiesto["etapas_completadas"].append(etapa)
        log.info("Etapa completada: %s", etapa)

    try:
        log.info("Inicio de la ejecucion %s (destino %s)", run_id, destino)
        raw = leer_fuente(cfg)
        manifiesto["fuente"] |= {"sha256": _huella(cfg["rutas"]["fuente"]), "filas": len(raw)}
        completar("lectura")

        resultados, df = calidad.validar(raw, cfg)
        calidad.escribir_reporte(resultados, carpeta)
        manifiesto["calidad"] = {r.control: r.estado for r in resultados}
        for r in resultados:
            nivel = logging.ERROR if r.estado == calidad.CRITICO else logging.WARNING if r.estado == calidad.ADVERTENCIA else logging.INFO
            log.log(nivel, "Control %s: %s - %s", r.control, r.estado, r.detalle)
        if calidad.hay_criticos(resultados):
            raise calidad.ControlCritico("Fallaron controles criticos: " + ", ".join(r.control for r in resultados if r.estado == calidad.CRITICO))
        completar("validacion")

        serie = proc.construir_serie(df, cfg)
        y = serie["destino"]
        serie.reset_index().assign(periodo=lambda d: d["periodo"].astype(str)).to_parquet(carpeta / "datos_preparados.parquet", index=False)
        completar("preparacion")

        origenes = proc.origenes(cfg)
        meses_eval = proc.rango(cfg["periodos"]["evaluacion"])
        est_eval, par_eval = proc.estimar(y, origenes["evaluacion"], meses_eval, k)
        completar("ajuste")

        ref_eval = proc.referencia(y, origenes["evaluacion"], meses_eval)
        obs_eval = y.reindex(meses_eval)
        met, met_ref = proc.metricas(obs_eval, est_eval), proc.metricas(obs_eval, ref_eval)
        evaluacion = pd.DataFrame({"observado": obs_eval, "estimado": est_eval, "referencia": ref_eval})
        evaluacion.index = evaluacion.index.astype(str)
        evaluacion.rename_axis("periodo").reset_index().to_parquet(carpeta / "evaluacion.parquet", index=False)
        log.info("Evaluacion %s a %s: MAE %.0f, MAPE %.2f %% (referencia MAE %.0f, MAPE %.2f %%)",
                 meses_eval[0], meses_eval[-1], met["MAE"], met["MAPE"], met_ref["MAE"], met_ref["MAPE"])
        completar("evaluacion")

        meses_est = proc.rango(cfg["periodos"]["estimacion"])
        if meses_est[0] != origenes["estimacion"] + 1:
            raise ValueError("periodos.estimacion debe empezar el mes siguiente al fin de la evaluacion")
        est_final, par_final = proc.estimar(y, origenes["estimacion"], meses_est, k)
        generado = datetime.now().isoformat(timespec="seconds")
        comunes = {"destino": destino, "unidad": unidad, "id_ejecucion": run_id, "fecha_generacion": generado, "version_procedimiento": version_proc}
        estimaciones = pd.DataFrame({"periodo": meses_est.astype(str), "valor": est_final.to_numpy(), "tipo_valor": "estimado"}).assign(**comunes)
        observados = pd.DataFrame({"periodo": y.dropna().index.astype(str), "valor": y.dropna().to_numpy(), "tipo_valor": "observado"}).assign(**comunes)
        completar("estimacion")

        decision = _regla_aceptacion(resultados, estimaciones, cfg, met, met_ref)
        estimaciones.to_parquet(carpeta / "estimaciones.parquet", index=False)
        observados.to_parquet(carpeta / "observados.parquet", index=False)
        metricas = {"procedimiento": met, "referencia": met_ref, "meses_evaluados": [str(meses_eval[0]), str(meses_eval[-1])]}
        (carpeta / "metricas.json").write_text(json.dumps(metricas, indent=2), encoding="utf-8")
        (carpeta / "parametros.json").write_text(json.dumps({"evaluacion": par_eval, "estimacion": par_final}, indent=2), encoding="utf-8")
        manifiesto |= {"metricas": metricas, "parametros": {"evaluacion": par_eval, "estimacion": par_final}, "aceptacion": decision}
        completar("almacenamiento")

        if decision["aprobada"]:
            _publicar(carpeta, salidas, run_id)
            manifiesto["estado"] = "publicada"
            completar("publicacion")
        else:
            manifiesto["estado"] = "rechazada"
            log.warning("Version rechazada por la regla de aceptacion: %s", decision["reglas"])
    except Exception as e:  # cualquier fallo deja intacta la version vigente
        manifiesto |= {"estado": "fallida", "error": f"{type(e).__name__}: {e}"}
        log.error("Ejecucion detenida en la etapa %s: %s", next((s for s in ETAPAS if s not in manifiesto["etapas_completadas"]), "?"), e)
    finally:
        manifiesto["fin"] = datetime.now().isoformat(timespec="seconds")
        (carpeta / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        log.info("Resultado: %s", manifiesto["estado"])
        for handler in list(log.handlers):
            handler.close()
            log.removeHandler(handler)
    manifiesto["carpeta"] = str(carpeta)
    return manifiesto


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline del observatorio (Laboratorio 11)")
    parser.add_argument("--config", default=str(CONFIG_DEFECTO))
    parser.add_argument("--fuente", help="Ruta a la base de migracion (prioridad sobre la configuracion)")
    parser.add_argument("--salidas", help="Carpeta de salidas (prioridad sobre la configuracion)")
    args = parser.parse_args(argv)
    resultado = ejecutar(cargar(args.config, fuente=args.fuente, salidas=args.salidas))
    return {"publicada": 0, "rechazada": 2}.get(resultado["estado"], 1)
