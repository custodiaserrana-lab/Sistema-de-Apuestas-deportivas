import streamlit as st
from main import analizar_jornada # Importa tu motor lógico

st.title("⚽ Predictor Fútbol 2026 v1.0")
st.sidebar.header("Configuración de Bankroll")
bankroll = st.sidebar.number_input("Bankroll Actual (ARS)", value=30000)

if st.button("Actualizar Jornada y Buscar Valor"):
    # Aquí la App ejecuta la descarga y los cálculos
    reporte = analizar_jornada("Argentina", "URL_CSV")
    st.write(reporte)
