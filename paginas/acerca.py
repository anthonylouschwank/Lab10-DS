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
- **Pronóstico**: estimación de valores futuros a partir del comportamiento pasado de la serie.
- **Error del pronóstico (MAE, RMSE, MAPE)**: qué tan lejos quedó el pronóstico del valor real.
  MAPE se expresa en porcentaje: un MAPE de 18 % significa que, en promedio, el pronóstico se
  desvió 18 % del valor real.
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
"""
)
