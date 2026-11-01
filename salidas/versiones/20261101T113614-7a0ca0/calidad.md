# Reporte de controles de calidad

| Control | Estado | Detalle |
|---|---|---|
| a_columnas_tipos | ok | Columnas y tipos completos |
| b_fechas_cobertura | ok | Fechas validas y cobertura completa de 2023-01 a 2026-06 |
| c_unicidad | ok | Sin claves repetidas; clave ['anio', 'mes', 'via', 'frontera', 'pais', 'agrupacion', 'tipo'] |
| d_faltantes | ok | Sin faltantes |
| e_valores_denominadores | ok | Conteos finitos y no negativos; denominadores de r mayores que cero |
| f_regla_metodologica | advertencia | el factor de reparto es un supuesto sin fuente documentada |
