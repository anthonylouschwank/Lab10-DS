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
paginas.run()
