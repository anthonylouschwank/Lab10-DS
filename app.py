"""Observatorio de turismo sostenible - Guatemala.

Ejecutar:
    streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Observatorio de Turismo - Guatemala",
    page_icon=":material/travel_explore:",
    layout="wide",
)

paginas = st.navigation(
    {
        "Observatorio": [
            st.Page("paginas/inicio.py", title="Inicio", icon=":material/home:", default=True),
            st.Page("paginas/explorar.py", title="Explorar llegadas", icon=":material/bar_chart:"),
            st.Page("paginas/modelos.py", title="Pronósticos y modelos", icon=":material/trending_up:"),
        ],
        "Ayuda": [
            st.Page("paginas/acerca.py", title="Glosario y limitaciones", icon=":material/help:"),
        ],
    }
)
paginas.run()
