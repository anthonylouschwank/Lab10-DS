"""Lectura del archivo de configuracion del pipeline."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DEFECTO = ROOT / "config" / "config.yaml"


def cargar(path: Path | str = CONFIG_DEFECTO, fuente: str | None = None, salidas: str | None = None) -> dict:
    """Lee el YAML y resuelve las rutas. OBS_FUENTE y OBS_SALIDAS tienen prioridad sobre el archivo."""
    path = Path(path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["_archivo"] = str(path.resolve())
    rutas = cfg["rutas"]
    rutas["fuente"] = fuente or os.environ.get("OBS_FUENTE") or rutas["fuente"]
    rutas["salidas"] = salidas or os.environ.get("OBS_SALIDAS") or rutas["salidas"]
    for clave, valor in rutas.items():
        p = Path(valor)
        rutas[clave] = p if p.is_absolute() else ROOT / p
    return cfg
