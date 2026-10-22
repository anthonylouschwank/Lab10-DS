import streamlit as st

st.title("Pronósticos y modelos")
st.info("Sección en construcción para la entrega final.", icon=":material/construction:")
st.markdown(
    """
Aquí se mostrarán los resultados de los modelos ya entrenados en los Laboratorios 1 y 2
(no se entrenan modelos nuevos):

- **Holt-Winters**, **SARIMA** y **Prophet** (Laboratorio 1).
- **LSTM** (Laboratorio 2).

Para cada serie (total mensual, fronteras y vías) se podrá comparar el valor real contra el
pronosticado, ver el error de cada modelo y entender en qué periodos falla más.
"""
)
