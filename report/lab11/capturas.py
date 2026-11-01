"""Capturas del tablero y de MLflow para el informe del Laboratorio 11 (Playwright + Chromium).

Requiere los servicios levantados (`docker compose up -d`). Uso:
    python report/lab11/capturas.py tablero estimaciones_vigente
    python report/lab11/capturas.py mlflow

Las imagenes quedan en report/lab11/capturas/. Complementan los registros de MLflow; no los sustituyen.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent.parent
CARPETA = AQUI / "capturas"
TABLERO = os.environ.get("URL_TABLERO", "http://127.0.0.1:8501")
MLFLOW = os.environ.get("URL_MLFLOW", "http://127.0.0.1:5000")


def _tablero(navegador, nombre: str) -> None:
    pagina = navegador.new_page(viewport={"width": 1440, "height": 2150}, device_scale_factor=2)
    pagina.goto(f"{TABLERO}/estimaciones")
    pagina.wait_for_selector("text=Visitantes observados y estimados", timeout=60_000)
    pagina.wait_for_timeout(2500)
    pagina.screenshot(path=CARPETA / f"{nombre}.png", full_page=True)
    pagina.close()
    recortar(f"{nombre}.png", (0, 0, 2880, 2950))


def _mlflow(navegador) -> None:
    pagina = navegador.new_page(viewport={"width": 1600, "height": 760}, device_scale_factor=2)
    pagina.goto(f"{MLFLOW}/#/experiments/1/runs?workflowType=machine_learning")
    pagina.wait_for_selector("text=matching runs", timeout=60_000)
    pagina.wait_for_timeout(2000)
    pagina.screenshot(path=CARPETA / "mlflow_ejecuciones.png")

    # Detalle de la ultima ejecucion publicada y de la ultima fallida, segun la evidencia de la consulta
    tabla = [l.split(",") for l in (ROOT / "evidencia" / "mlflow_ejecuciones.csv").read_text(encoding="utf-8").splitlines()[1:]]
    for estado, archivo in (("publicada", "mlflow_run_publicada.png"), ("fallida", "mlflow_run_fallida.png")):
        run = next(f for f in reversed(tabla) if f[3] == estado)
        pagina.goto(f"{MLFLOW}/#/experiments/1/runs/{run[1]}")
        pagina.wait_for_selector("text=Parameters", timeout=60_000)
        pagina.wait_for_timeout(2000)
        pagina.set_viewport_size({"width": 1600, "height": 1500})
        pagina.screenshot(path=CARPETA / archivo)
        pagina.set_viewport_size({"width": 1600, "height": 760})
    pagina.close()
    # Sin la barra lateral ni el panel del asistente: solo el detalle del run
    recortar("mlflow_ejecuciones.png", (0, 0, 2368, 1520))
    recortar("mlflow_run_publicada.png", (402, 0, 2350, 2810))
    recortar("mlflow_run_fallida.png", (402, 0, 2350, 2590))


def recortar(archivo: str, caja: tuple[int, int, int, int]) -> None:
    imagen = Image.open(CARPETA / archivo)
    imagen.crop(caja).save(CARPETA / archivo)


def main(argv: list[str]) -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=os.environ.get("BROWSER_PATH") or None)
        if argv[0] == "tablero":
            _tablero(navegador, argv[1])
        else:
            _mlflow(navegador)
        navegador.close()
    print(json.dumps(sorted(f.name for f in CARPETA.iterdir())))


if __name__ == "__main__":
    main(sys.argv[1:])
