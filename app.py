"""Observatorio de turismo sostenible - Guatemala.

Ejecutar:
    streamlit run app.py
"""

import streamlit as st

from src.ui import FUENTE_DATOS, estilo_global

st.set_page_config(
    page_title="Observatorio de Turismo · Guatemala",
    page_icon="static/icono.svg",
    layout="wide",
)
st.logo("static/logo.svg", icon_image="static/icono.svg", size="large")
estilo_global()

paginas = st.navigation(
    {
        "Observatorio": [
            st.Page("paginas/inicio.py", title="Inicio", icon=":material/home:", default=True),
        ],
        "Explorar los datos": [
            st.Page("paginas/explorar.py", title="Evolución y origen", icon=":material/bar_chart:"),
            st.Page("paginas/temporadas.py", title="Temporadas", icon=":material/calendar_month:"),
            st.Page("paginas/mercados.py", title="Mercados y recuperación", icon=":material/public:"),
        ],
        "Pronósticos": [
            st.Page("paginas/modelos.py", title="Pronósticos de llegadas", icon=":material/trending_up:"),
            st.Page("paginas/comparar.py", title="Comparar modelos", icon=":material/leaderboard:"),
        ],
        "Ayuda": [
            st.Page("paginas/acerca.py", title="Glosario y limitaciones", icon=":material/help:"),
        ],
    }
)
st.sidebar.caption(FUENTE_DATOS)
st.sidebar.caption(
    "Equipo: Anthony Lou Schwank · Christa Isabella Obando Guzmán · "
    "Fabian Prado Dluzniewski · Luis Fernando Mendoza Alvarez"
)
paginas.run()
