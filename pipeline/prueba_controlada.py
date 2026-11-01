"""Prueba controlada de fallo y recuperacion (Laboratorio 11, ejercicio 7.4).

Uso:
    python -m pipeline.prueba_controlada --problema columna      # quita la columna Viajero
    python -m pipeline.prueba_controlada --problema duplicado    # repite una fila de turistas
    python -m pipeline.prueba_controlada --problema denominador  # deja en cero la ventana del denominador de r

1. Copia la fuente configurada a una carpeta temporal e introduce el problema en la copia.
2. Ejecuta el pipeline con la copia: debe fallar en el control correspondiente.
3. Verifica que vigente.json y los archivos de la version aprobada siguen iguales.
4. Corrige la copia (vuelve a los datos originales) y ejecuta de nuevo: debe publicarse.
Las dos ejecuciones quedan en MLflow. La fuente original nunca se modifica.
Escribe evidencia/prueba_controlada_<problema>.md. Codigo de salida 0 si todo se comporto como se espera.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import tempfile
from pathlib import Path

import pandas as pd

from pipeline import procedimiento as proc
from pipeline.configuracion import CONFIG_DEFECTO, ROOT, cargar
from pipeline.run import ejecutar, leer_fuente

CONTROL_ESPERADO = {"columna": "a_columnas_tipos", "duplicado": "c_unicidad", "denominador": "e_valores_denominadores"}


def introducir(raw: pd.DataFrame, problema: str, cfg: dict) -> tuple[pd.DataFrame, str]:
    """Devuelve una copia con el problema y su descripcion."""
    columnas = {v: k for k, v in cfg["fuente"]["columnas"].items()}
    tipo, conteo = columnas["tipo"], columnas["viajeros"]
    if problema == "columna":
        return raw.drop(columns=conteo), f"se elimino la columna indispensable `{conteo}`"
    if problema == "duplicado":
        fila = raw[raw[tipo] == "Turista"].head(1)
        return pd.concat([raw, fila], ignore_index=True), "se repitio una fila de turistas (misma clave anio-mes-via-frontera-pais-agrupacion-tipo)"
    if problema == "denominador":
        origen = proc.origenes(cfg)["evaluacion"]
        k = cfg["procedimiento"]["ventana_nivel"]
        inicio, fin = origen - k + 1 - 12, origen - 12
        meses = raw[columnas["anio"]] * 12 + raw[columnas["mes"]]
        malo = raw.copy()
        malo.loc[meses.between(inicio.year * 12 + inicio.month, fin.year * 12 + fin.month), conteo] = 0
        return malo, f"se dejaron en cero los conteos de {inicio} a {fin} (denominador de r para el origen {origen})"
    raise ValueError(f"Problema desconocido: {problema}")


def _huella_version(carpeta: Path) -> str:
    h = hashlib.sha256()
    for archivo in sorted(carpeta.iterdir()):
        h.update(archivo.name.encode() + archivo.read_bytes())
    return h.hexdigest()


def _vigente(salidas: Path) -> tuple[dict | None, str | None]:
    archivo = salidas / "vigente.json"
    if not archivo.exists():
        return None, None
    info = json.loads(archivo.read_text(encoding="utf-8"))
    return info, _huella_version(salidas / info["ruta"])


def _con_fuente(cfg: dict, fuente: Path) -> dict:
    """Misma configuracion, otra fuente."""
    nueva = copy.deepcopy(cfg)
    nueva["rutas"]["fuente"] = fuente
    return nueva


def correr(cfg: dict, problema: str, evidencia: Path) -> dict:
    salidas: Path = cfg["rutas"]["salidas"]
    original = leer_fuente(cfg)
    malo, descripcion = introducir(original, problema, cfg)
    antes, huella_antes = _vigente(salidas)

    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / "copia_con_problema.parquet"
        malo.to_parquet(copia, index=False)
        fallida = ejecutar(_con_fuente(cfg, copia))
        despues, huella_despues = _vigente(salidas)

        corregida = Path(tmp) / "copia_corregida.parquet"
        original.to_parquet(corregida, index=False)
        recuperada = ejecutar(_con_fuente(cfg, corregida))
    final, _ = _vigente(salidas)

    control = CONTROL_ESPERADO[problema]
    resumen = {
        "problema": problema,
        "descripcion": descripcion,
        "fallida": fallida["id_ejecucion"],
        "estado_fallida": fallida["estado"],
        "control_detectado": fallida.get("calidad", {}).get(control),
        "error": fallida.get("error"),
        "vigente_antes": antes["id_ejecucion"] if antes else None,
        "vigente_despues_del_fallo": despues["id_ejecucion"] if despues else None,
        "version_intacta": huella_antes == huella_despues,
        "recuperada": recuperada["id_ejecucion"],
        "estado_recuperada": recuperada["estado"],
        "vigente_final": final["id_ejecucion"] if final else None,
    }
    resumen["comportamiento_esperado"] = (
        resumen["estado_fallida"] == "fallida"
        and resumen["control_detectado"] == "critico"
        and resumen["vigente_antes"] == resumen["vigente_despues_del_fallo"]
        and resumen["version_intacta"]
        and resumen["estado_recuperada"] == "publicada"
        and resumen["vigente_final"] == resumen["recuperada"]
    )
    _escribir(resumen, evidencia / f"prueba_controlada_{problema}.md")
    return resumen


def _escribir(r: dict, archivo: Path) -> None:
    archivo.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        f"# Prueba controlada: {r['problema']}",
        "",
        f"1. Problema introducido en una copia de la fuente: {r['descripcion']}.",
        f"2. Ejecucion con la copia: `{r['fallida']}`, estado **{r['estado_fallida']}**; control `{CONTROL_ESPERADO[r['problema']]}` = {r['control_detectado']}.",
        f"   Causa registrada: {r['error']}",
        f"3. Version vigente antes del fallo: `{r['vigente_antes']}`; despues del fallo: `{r['vigente_despues_del_fallo']}`. "
        f"Archivos de la version aprobada sin cambios: {'si' if r['version_intacta'] else 'NO'}.",
        f"4. Copia corregida y nueva ejecucion: `{r['recuperada']}`, estado **{r['estado_recuperada']}**; version vigente final `{r['vigente_final']}`.",
        "",
        f"Resultado: {'el pipeline detecto el problema, conservo la version aprobada y se recupero' if r['comportamiento_esperado'] else 'COMPORTAMIENTO INESPERADO, revisar'}.",
    ]
    archivo.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prueba controlada de fallo y recuperacion")
    parser.add_argument("--problema", choices=list(CONTROL_ESPERADO), default="columna")
    parser.add_argument("--config", default=str(CONFIG_DEFECTO))
    parser.add_argument("--fuente")
    parser.add_argument("--salidas")
    parser.add_argument("--evidencia", default=str(ROOT / "evidencia"))
    args = parser.parse_args(argv)
    resumen = correr(cargar(args.config, fuente=args.fuente, salidas=args.salidas), args.problema, Path(args.evidencia))
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0 if resumen["comportamiento_esperado"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
