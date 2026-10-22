import streamlit as st

st.title("Observatorio de Turismo Sostenible · Guatemala")
st.markdown(
    "Tablero para directivos y tomadores de decisiones del sector turístico. "
    "Permite explorar cómo llegan los viajeros internacionales a Guatemala, de dónde vienen "
    "y qué se espera para los próximos meses según modelos de pronóstico."
)

st.subheader("Preguntas que responde")
st.markdown(
    """
1. ¿Cómo ha evolucionado la llegada de viajeros internacionales y cuánto se recuperó tras la pandemia?
2. ¿En qué meses se concentra la demanda (temporadas altas y bajas)?
3. ¿Por qué vías y puestos fronterizos ingresan los viajeros?
4. ¿De qué regiones y países provienen, y cómo cambia esa mezcla en el tiempo?
5. ¿Cuántos viajeros se esperan en los próximos meses y qué tan confiables son esos pronósticos?
6. ¿Qué modelo de pronóstico funciona mejor para cada serie?
"""
)

st.subheader("Cómo navegar")
c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("paginas/explorar.py", label="Explorar llegadas", icon=":material/bar_chart:")
    st.caption("Evolución por vía, origen de los viajeros y puestos de ingreso. Las gráficas están enlazadas.")
with c2:
    st.page_link("paginas/modelos.py", label="Pronósticos y modelos", icon=":material/trending_up:")
    st.caption("Resultados de los modelos de los Laboratorios 1 y 2 y comparación de su desempeño.")
with c3:
    st.page_link("paginas/acerca.py", label="Glosario y limitaciones", icon=":material/help:")
    st.caption("Qué significa cada término y qué no se puede concluir con estos datos.")

st.info(
    "Los datos son de uso exclusivamente académico y no corresponden a cifras oficiales del INGUAT "
    "ni del Instituto Guatemalteco de Migración.",
    icon=":material/info:",
)
