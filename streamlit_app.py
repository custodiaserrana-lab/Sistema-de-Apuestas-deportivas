import streamlit as st
import pandas as pd
import subprocess

st.title("Futbol Quant Bot")

st.write("Sistema de detección de Value Bets")

if st.button("Ejecutar análisis de mercado"):

    subprocess.run(["python", "main.py"])

    st.success("Análisis completado")

try:

    df = pd.read_csv("reports/value_bets.csv")

    st.subheader("Value Bets detectadas")

    st.dataframe(df)

except:

    st.warning("Todavía no hay reportes generados")
