"""Glosario, guia de colores y limitaciones de los datos y de los modelos."""

import streamlit as st

from src.ui import encabezado_pagina

encabezado_pagina(
    "Ayuda",
    "Glosario y limitaciones",
    "Qué significa cada término del tablero, cómo leer sus colores y qué no se puede concluir con estos datos.",
)

glosario, colores, limites = st.tabs(["Glosario", "Cómo leer los colores", "Limitaciones"])

with glosario:
    st.markdown(
        """
**Turista.** Viajero que pasa al menos una noche en el país.

**Excursionista.** Viajero que entra y sale el mismo día.

**Vía de ingreso.** Medio por el que entró el viajero: aérea, terrestre o marítima.

**Puesto de ingreso.** Aeropuerto, puerto o paso fronterizo donde se registró la entrada.

**Región OMT.** Agrupación de países de origen definida por la Organización Mundial del Turismo.

**Índice de recuperación.** Viajeros de un año divididos entre los del año base en los mismos meses, multiplicado
por 100. Un índice de 120 equivale a 20 % más que el año base; uno de 60, a 40 % menos.

**Pronóstico.** Estimación de valores futuros a partir del comportamiento pasado de una serie.

**Periodo de entrenamiento y periodo de prueba.** Los modelos aprendieron con los datos de enero de 2009 a marzo
de 2021 y pronosticaron de abril de 2021 a junio de 2026 sin ver lo que ocurrió. Comparar esos pronósticos con la
realidad mide su confiabilidad.

**Validación.** Meses previos al corte que el modelo no usó para aprender y que sirven para elegir su
configuración sin tocar el periodo de prueba.

**Medidas de error.** Indican qué tan lejos quedó el pronóstico del valor real.
- **MAE:** error promedio, en viajeros por mes.
- **RMSE:** también en viajeros, pero pesa más los errores grandes.
- **MAPE:** error promedio como porcentaje del valor real. Un MAPE de 18 % indica que el pronóstico se desvió,
  en promedio, 18 %. Se dispara cuando hay meses con muy pocos viajeros.

**Rango probable (95 %).** Banda en la que el modelo esperaba encontrar el valor real con 95 % de probabilidad.
Solo SARIMA y Prophet la calculan.

**Referencia ingenua.** Repetir los valores del último año conocido. Es la vara mínima: un modelo que no la supera
no aporta información.

**Holt-Winters, SARIMA y Prophet** (Laboratorio 1) **y LSTM** (Laboratorio 2). Los modelos comparados; la página
*Pronósticos de llegadas* describe cada uno.
"""
    )

with colores:
    st.markdown(
        """
Cada color significa lo mismo en todo el tablero.

- **Vías de ingreso:** :blue[**azul**] para la aérea, :orange[**naranja**] para la terrestre y :green[**verde aqua**] para la marítima.
- **Mapas de calor:** un solo tono de azul; cuanto más oscuro, más viajeros (o más error, en la comparación de modelos).
- **Índice de recuperación:** rojo por debajo del año base, gris en un nivel similar y azul por encima.
- **Modelos:** violeta para Holt-Winters, rosa para SARIMA, amarillo para Prophet, verde para la LSTM y gris
  punteado para la referencia ingenua. Cada modelo tiene además su propio tipo de línea, de modo que se distingue
  aunque no se perciban los colores.
- **Negro:** valor real observado.

La paleta se validó para las formas comunes de daltonismo. Cuando un color tiene poco contraste con el fondo, el
valor exacto aparece al pasar el cursor y en las tablas.
"""
    )

with limites:
    st.markdown(
        """
- **Uso académico.** Los datos no son cifras oficiales.
- **Tres fuentes distintas.** La base combina respaldos históricos (2009-2020), registros del Instituto
  Guatemalteco de Migración (2021-2022) y conteos depurados del INGUAT (2023 a junio de 2026). Parte de los
  cambios entre esos periodos puede deberse al registro y no a la demanda.
- **Países agrupados desde 2023.** La columna de país agrupa a veces mercados en lugar de países individuales.
- **2026 incompleto.** Solo incluye de enero a junio.
- **Qué, no por qué.** Las gráficas muestran lo que ocurrió; con estos datos no se puede atribuir un cambio a una
  causa concreta.
- **Vía marítima.** Desde 2017 la fuente solo registra cruceristas y otros tipos de viajero por esa vía, no
  turistas ni excursionistas, así que sus pronósticos no pueden evaluarse.
- **Periodo de prueba atípico.** Los modelos se evaluaron durante la reapertura posterior a la pandemia; en un
  periodo estable su error podría ser distinto. No hay pronósticos posteriores a junio de 2026 y el tablero no
  entrena modelos nuevos.
- **Contrastar antes de decidir.** Cualquier recomendación derivada del tablero debe tener en cuenta estas
  limitaciones y verificarse con otras fuentes, como la ocupación hotelera, la conectividad aérea o el gasto turístico.
"""
    )
