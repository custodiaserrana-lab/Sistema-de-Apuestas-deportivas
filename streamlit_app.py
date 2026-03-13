import streamlit as st
import pandas as pd
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

st.set_page_config(page_title="Futbol Quant Bot", page_icon="⚽")
st.title("⚽ Futbol Quant Bot")
st.write("Sistema de análisis cuantitativo con detección de Value Bets")

tab1, tab2 = st.tabs(["📊 Backtesting histórico", "🔍 Detección en vivo"])

# -----------------------------------------------
# TAB 1 — BACKTESTING (usa app.py)
# -----------------------------------------------
with tab1:
    st.subheader("Backtesting histórico por liga")

    if st.button("Ejecutar backtesting"):
        try:
            import app
            with st.spinner("Analizando datos históricos..."):
                apuestas, resumen = app.run()

            st.success(f"Completado — {len(apuestas)} apuestas analizadas")

            st.subheader("Resumen por liga")
            st.dataframe(pd.DataFrame(resumen))

            if apuestas:
                st.subheader("Detalle de apuestas")
                st.dataframe(pd.DataFrame(apuestas))

        except Exception as e:
            st.error(f"Error en backtesting: {e}")

    roi_path = os.path.join(BASE_DIR, "reports", "roi_historial.csv")
    if os.path.exists(roi_path):
        st.subheader("Historial ROI")
        st.dataframe(pd.read_csv(roi_path))

# -----------------------------------------------
# TAB 2 — DETECCION EN VIVO (usa main.py)
# -----------------------------------------------
with tab2:
    st.subheader("Detección de Value Bets en próximos partidos")

    if st.button("Ejecutar análisis de mercado"):
        try:
            import main
            with st.spinner("Analizando mercados..."):
                apuestas = main.run()

            if apuestas:
                st.success(f"{len(apuestas)} value bets detectadas")
                st.dataframe(pd.DataFrame(apuestas))
            else:
                st.info("No se detectaron value bets en esta jornada.")

        except Exception as e:
            st.error(f"Error en detección en vivo: {e}")

    csv_path = os.path.join(BASE_DIR, "reports", "value_bets.csv")
    if os.path.exists(csv_path):
        st.subheader("Último reporte guardado")
        st.dataframe(pd.read_csv(csv_path))
