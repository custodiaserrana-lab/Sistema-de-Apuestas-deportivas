import streamlit as st
import pandas as pd
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

st.title("Futbol Quant Bot")
st.write("Sistema de detección de Value Bets")

if st.button("Ejecutar análisis de mercado"):
    try:
        import main
        with st.spinner("Analizando mercados..."):
            apuestas = main.run()
        if apuestas:
            st.success(f"Análisis completado — {len(apuestas)} value bets detectadas")
        else:
            st.info("Análisis completado. No se detectaron value bets en esta jornada.")
    except Exception as e:
        st.error(f"Error al ejecutar el análisis: {e}")

csv_path = os.path.join(BASE_DIR, "reports", "value_bets.csv")

try:
    df = pd.read_csv(csv_path)
    st.subheader("Value Bets detectadas")
    st.dataframe(df)
except FileNotFoundError:
    st.warning("Todavía no hay reportes. Ejecutá el análisis primero.")
except Exception as e:
    st.warning(f"No se pudo cargar el reporte: {e}")
