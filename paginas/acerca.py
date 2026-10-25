import streamlit as st

st.title("Glosario y limitaciones")

st.subheader("Glosario")
st.markdown(
    """
- **Turista**: viajero que pernocta al menos una noche en el país.
- **Excursionista**: viajero que entra y sale el mismo día, sin pernoctar.
- **Vía de ingreso**: medio por el que entró el viajero (aérea, terrestre o marítima).
- **Frontera / puesto de ingreso**: aeropuerto, puerto o paso fronterizo donde se registró la entrada.
- **Región OMT**: agrupación de países de origen definida por la Organización Mundial del Turismo.
- **Índice de recuperación (año base = 100)**: viajeros de un año divididos entre los del año base
  en los mismos meses, por 100. 120 = 20 % más que el año base; 60 = 40 % menos.
- **Pronóstico**: estimación de valores futuros a partir del comportamiento pasado de la serie.
- **Periodo de entrenamiento / de prueba**: los modelos aprendieron con enero 2009-marzo 2021 y
  pronosticaron abril 2021-junio 2026 sin ver esos datos; comparar ese pronóstico con lo que
  realmente pasó mide su confiabilidad.
- **Error del pronóstico**: qué tan lejos quedó el pronóstico del valor real.
  - **MAE**: error promedio en viajeros por mes.
  - **RMSE**: parecido al MAE pero castiga más los errores grandes.
  - **MAPE**: error promedio en porcentaje del valor real; un MAPE de 18 % significa que, en
    promedio, el pronóstico se desvió 18 %. Se dispara cuando hay meses con muy pocos viajeros.
- **Rango probable (95 %)**: banda dentro de la cual el modelo esperaba el valor real con 95 % de
  probabilidad. Solo SARIMA y Prophet la calculan.
- **Referencia ingenua**: repetir los valores del último año conocido. Es la vara mínima que un
  modelo debe superar para ser útil.
- **Holt-Winters, SARIMA, Prophet** (Laboratorio 1) y **LSTM** (Laboratorio 2): los modelos de
  pronóstico comparados. Su descripción está en la página *Pronósticos de llegadas*.
- **Validación**: datos previos al corte que el modelo no usó para aprender y que sirven para
  elegir su configuración sin mirar el periodo de prueba.
"""
)

st.subheader("Cómo leer los colores")
st.markdown(
    """
Cada color significa **lo mismo en todo el tablero**:

- :blue[**Azul**] = vía aérea · :orange[**Naranja**] = vía terrestre · :green[**Verde aqua**] = vía marítima.
- En los mapas de calor, un solo tono de azul: **más oscuro = más viajeros** (o más error, en la comparación de modelos).
- En el índice de recuperación: **rojo** = por debajo del año base, **gris** = similar, **azul** = por encima.
- Modelos: violeta = Holt-Winters, rosa = SARIMA, amarillo = Prophet, verde = LSTM, gris punteado =
  referencia ingenua. Cada modelo además tiene su propio tipo de línea para distinguirlo sin depender del color.
- **Negro** = valor real observado.
"""
)

st.subheader("Limitaciones")
st.markdown(
    """
- Los datos son de **uso académico** y no son cifras oficiales.
- La base combina tres fuentes: respaldos históricos (2009-2020), Instituto Guatemalteco de
  Migración (2021-2022) y conteos depurados del INGUAT (2023-junio 2026).
- Desde 2023 la columna de país a veces agrupa **mercados** en lugar de países individuales.
- El año 2026 solo incluye datos hasta junio.
- Las gráficas muestran **qué** ocurrió, no **por qué**: un cambio en las llegadas no puede
  atribuirse a una causa específica solo con estos datos.
- Por vía marítima, desde 2017 la fuente solo registra cruceristas u otros tipos de viajero (no
  turistas ni excursionistas), por lo que los pronósticos de esa serie no
  pueden evaluarse.
- Los modelos se evaluaron en un periodo que incluye la reapertura posterior a la pandemia; su
  error en un periodo estable podría ser distinto. Los laboratorios no generaron pronósticos
  posteriores a junio de 2026 y en este tablero no se entrenan modelos nuevos.
- Las recomendaciones que se deriven del tablero deben considerar estas limitaciones y contrastarse
  con otras fuentes (ocupación hotelera, conectividad aérea, gasto turístico).
"""
)
