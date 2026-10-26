"""Acerca de: glosario, lectura de colores, limitaciones y equipo."""

import streamlit as st

from src.ui import encabezado_pagina

encabezado_pagina("Ayuda", "Acerca del tablero")

glosario, colores, limites, equipo = st.tabs(["Glosario", "Colores", "Limitaciones", "Equipo y fuentes"])

with glosario:
    st.markdown(
        """
| Término | Significado |
|---|---|
| Turista | Viajero que pasa al menos una noche en el país. |
| Excursionista | Viajero que entra y sale el mismo día. |
| Vía de ingreso | Medio por el que entró el viajero: aérea, terrestre o marítima. |
| Puesto de ingreso | Aeropuerto, puerto o paso fronterizo donde se registró la entrada. |
| Región OMT | Agrupación de países de origen de la Organización Mundial del Turismo. |
| Índice de recuperación | Viajeros de un año entre los del año base en los mismos meses, por 100. Un índice de 120 equivale a 20 % más que el año base. |
| Periodo de entrenamiento | Enero de 2009 a marzo de 2021: los datos con los que aprendieron los modelos. |
| Periodo de prueba | Abril de 2021 a junio de 2026: los modelos pronosticaron estos meses sin verlos. |
| Validación | Meses previos al corte, no usados para aprender, con los que se eligió la configuración de la LSTM. |
| MAE | Error promedio en viajeros por mes. |
| RMSE | Error en viajeros que castiga más los errores grandes. |
| MAPE | Error promedio como porcentaje del valor real. Se dispara en meses con muy pocos viajeros. |
| Rango probable (95 %) | Banda en la que el modelo esperaba el valor real con 95 % de probabilidad. Solo SARIMA y Prophet la calculan. |
| Referencia ingenua | Repite el último año conocido. Un modelo útil debe superarla. |
"""
    )

with colores:
    st.markdown(
        """
| Color | Significado |
|---|---|
| :blue[■] Azul | Vía aérea |
| :orange[■] Naranja | Vía terrestre |
| :green[■] Verde aqua | Vía marítima |
| Escala de azules | Magnitud: más oscuro, más viajeros (o más error en la comparación de modelos) |
| Rojo · gris · azul | Índice de recuperación: por debajo, similar o por encima del año base |
| Violeta, rosa, amarillo, verde | Holt-Winters, SARIMA, Prophet y LSTM; cada uno con su propio tipo de línea |
| Gris punteado | Referencia ingenua |
| Negro | Valor real observado |

La paleta se validó para las formas comunes de daltonismo. Los colores con poco contraste se acompañan
del valor exacto en el tooltip y en las tablas.
"""
    )

with limites:
    st.markdown(
        """
- Los datos son de uso académico y no constituyen estadísticas oficiales.
- La base combina respaldos históricos (2009-2020), registros del Instituto Guatemalteco de Migración (2021-2022) y
  conteos depurados del INGUAT (2023 a junio de 2026). Parte de los cambios entre esos periodos puede deberse al registro.
- Desde 2023 la columna de país agrupa algunos mercados.
- 2026 incluye solo de enero a junio.
- Las gráficas describen lo ocurrido; los datos no permiten atribuir un cambio a una causa concreta.
- Desde 2017 la fuente solo registra cruceristas y otros tipos de viajero por vía marítima, por lo que esa serie
  no se puede evaluar en el periodo de prueba.
- Los modelos se evaluaron durante la reapertura posterior a la pandemia y no hay pronósticos posteriores a junio de 2026.
- Cualquier decisión basada en el tablero debe contrastarse con otras fuentes, como ocupación hotelera, conectividad aérea o gasto turístico.
"""
    )

with equipo:
    st.markdown(
        """
**Equipo.** Anthony Lou Schwank, Christa Isabella Obando Guzmán, Fabian Prado Dluzniewski y Luis Fernando Mendoza Alvarez.
CC3066 Data Science, Universidad del Valle de Guatemala, 2026.

**Datos.** Base de migración de enero de 2009 a junio de 2026, de uso académico.

**Modelos.** Holt-Winters, SARIMA y Prophet (Laboratorio 1) y LSTM (Laboratorio 2), integrados sin reentrenar.

**Código.** [github.com/anthonylouschwank/Lab10-DS](https://github.com/anthonylouschwank/Lab10-DS)
"""
    )
