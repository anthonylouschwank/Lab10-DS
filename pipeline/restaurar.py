"""Restaura una version aprobada anterior (Laboratorio 11, ejercicio 7.5).

Uso:
    python -m pipeline.restaurar --listar          # versiones aprobadas; * marca la vigente
    python -m pipeline.restaurar --anterior        # vuelve a la version que estaba antes de la vigente
    python -m pipeline.restaurar --id <id>         # apunta a una version concreta

Solo cambia salidas/vigente.json (de forma atomica). No borra ni modifica ninguna version, asi que
siempre se puede volver a la mas reciente con --anterior o --id. El tablero lee la nueva version
en cuanto se recarga la pagina.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from pipeline.configuracion import CONFIG_DEFECTO, cargar
from pipeline.run import escribir_vigente

ARCHIVOS_REQUERIDOS = ["estimaciones.parquet", "observados.parquet", "metricas.json", "config.yaml"]


def versiones(salidas: Path) -> list[str]:
    carpeta = salidas / "versiones"
    return sorted(p.name for p in carpeta.iterdir() if p.is_dir()) if carpeta.exists() else []


def vigente(salidas: Path) -> dict | None:
    archivo = salidas / "vigente.json"
    return json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else None


def restaurar(salidas: Path, run_id: str) -> dict:
    """Apunta vigente.json a una version aprobada existente y completa."""
    carpeta = salidas / "versiones" / run_id
    if not carpeta.is_dir():
        raise FileNotFoundError(f"No existe la version aprobada {run_id}; disponibles: {versiones(salidas)}")
    faltan = [a for a in ARCHIVOS_REQUERIDOS if not (carpeta / a).exists()]
    if faltan:
        raise ValueError(f"La version {run_id} esta incompleta, faltan {faltan}")
    actual = vigente(salidas)
    # Ultima version que publico el pipeline: volver a ella no cuenta como restaurar una anterior
    ultima = (actual.get("ultima_publicada") or actual["id_ejecucion"]) if actual else None
    nuevo = {
        "id_ejecucion": run_id,
        "ruta": f"versiones/{run_id}",
        "publicado": datetime.now().isoformat(timespec="seconds"),
        "anterior": (actual["id_ejecucion"] if actual["id_ejecucion"] != run_id else actual.get("anterior")) if actual else None,
        "restaurada": run_id != ultima,
        "ultima_publicada": ultima,
    }
    escribir_vigente(salidas, nuevo)
    return nuevo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Restaurar una version aprobada")
    parser.add_argument("--config", default=str(CONFIG_DEFECTO))
    parser.add_argument("--salidas", help="Carpeta de salidas (prioridad sobre la configuracion)")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--listar", action="store_true")
    grupo.add_argument("--anterior", action="store_true")
    grupo.add_argument("--id")
    args = parser.parse_args(argv)
    salidas: Path = cargar(args.config, salidas=args.salidas)["rutas"]["salidas"]

    actual = vigente(salidas)
    if args.listar:
        for v in versiones(salidas):
            print(("* " if actual and v == actual["id_ejecucion"] else "  ") + v)
        return 0
    destino = args.id or (actual or {}).get("anterior")
    if not destino:
        print("No hay version anterior registrada en vigente.json; use --id")
        return 1
    try:
        nuevo = restaurar(salidas, destino)
    except (FileNotFoundError, ValueError) as e:
        print(f"No se restauro: {e}")
        return 1
    print(f"Version vigente: {nuevo['id_ejecucion']} (antes {nuevo['anterior']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
