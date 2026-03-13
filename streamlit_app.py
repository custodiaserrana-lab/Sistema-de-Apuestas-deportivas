import streamlit as st
import pandas as pd
import sys
import os

# Ruta base del proyecto (siempre correcta sin importar desde dónde se ejecute)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.title("Futbol Quant Bot")
st.write("Sistema de detección de Value Bets")

if st.button("Ejecutar análisis de mercado"):
    try:
        # Importar y ejecutar main directamente, sin subprocess
        sys.path.insert(0, BASE_DIR)
        import main
        # Si main.py tiene una función principal, llamarla así:
        # main.run()  ← descomentá esto si main.py tiene una función
        st.success("Análisis completado")
    except Exception as e:
        st.error(f"Error al ejecutar el análisis: {e}")

# Ruta absoluta al CSV
csv_path = os.path.join(BASE_DIR, "reports", "value_bets.csv")

try:
    df = pd.read_csv(csv_path)
    st.subheader("Value Bets detectadas")
    st.dataframe(df)
except FileNotFoundError:
    st.warning("Todavía no hay reportes. Ejecutá el análisis primero.")
except Exception as e:
    st.warning(f"No se pudo cargar el reporte: {e}")
