# Consulta de ejecuciones en MLflow

Experimento `observatorio-lago-de-atitlan` en `http://mlflow:5000`. 8 ejecuciones; tabla completa en `mlflow_ejecuciones.csv`.

| Ejecucion | Estado | MLflow | Commit | Fuente | MAE | MAPE % | Ref. MAE | Causa del fallo |
|---|---|---|---|---|---|---|---|---|
| 20261101T173335-b4655f | publicada | FINISHED | 7cafe5b802 | cdaba77918 | 4,458 | 11.14 | 6,138 |  |
| 20261101T113603-7aa3b6 | publicada | FINISHED | 698023e2b5 | cdaba77918 | 4,458 | 11.14 | 6,138 |  |
| 20261101T113614-7a0ca0 | publicada | FINISHED | 698023e2b5 | cdaba77918 | 4,458 | 11.14 | 6,138 |  |
| 20261101T113642-74246e | fallida | FAILED | 698023e2b5 | 8f78dc8a01 |  |  |  | ControlCritico: Fallaron controles criticos: a_columnas_tipos (Faltan columnas indispensables: ['Viajero']) |
| 20261101T113642-993761 | publicada | FINISHED | 698023e2b5 | f6fdbce2db | 4,458 | 11.14 | 6,138 |  |
| 20261101T113653-a51e91 | fallida | FAILED | 698023e2b5 | be6082ced6 |  |  |  | ControlCritico: Fallaron controles criticos: c_unicidad (2 filas con clave repetida (2 en tipos usados); clave ['anio', 'mes', 'via', 'frontera', 'pais', 'agrup |
| 20261101T113653-87a4ab | publicada | FINISHED | 698023e2b5 | f6fdbce2db | 4,458 | 11.14 | 6,138 |  |
| 20261101T113708-33f338 | publicada | FINISHED | 698023e2b5 | cdaba77918 | 4,458 | 11.14 | 6,138 |  |

## Ejecuciones fallidas

- 20261101T113642-74246e: ControlCritico: Fallaron controles criticos: a_columnas_tipos (Faltan columnas indispensables: ['Viajero']). Etapas completadas: lectura; sin metricas (se detuvo antes de evaluar).
- 20261101T113653-a51e91: ControlCritico: Fallaron controles criticos: c_unicidad (2 filas con clave repetida (2 en tipos usados); clave ['anio', 'mes', 'via', 'frontera', 'pais', 'agrupacion', 'tipo']). Etapas completadas: lectura; sin metricas (se detuvo antes de evaluar).

## Reproducibilidad

20261101T113614-7a0ca0 y 20261101T113708-33f338 (misma huella de fuente y de configuracion): 6 periodos comparados, diferencia maxima 0 visitantes, diferencia de MAE 0, tolerancia 1e-06. Resultado: equivalentes.
