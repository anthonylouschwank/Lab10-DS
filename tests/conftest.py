"""Las pruebas registran en un MLflow local temporal (SQLite), nunca en el servidor del equipo."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def mlflow_temporal(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("mlflow")
    os.environ["MLFLOW_TRACKING_URI"] = f"sqlite:///{carpeta / 'mlflow.db'}"
    os.environ["OBS_MLFLOW_ARTEFACTOS"] = (carpeta / "artefactos").as_uri()
    yield carpeta
