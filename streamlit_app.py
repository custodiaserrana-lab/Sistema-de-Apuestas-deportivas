import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime, timedelta, timezone
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ===============================
# CONFIGURACION DE PAGINA
# ===============================

st.set_page_config(
    page_title="Futbol Quant Bot",
    page_icon="⚽",
    layout="wide"
)

# ===============================
# ESTILOS PERSONALIZADOS
# ===============================

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .rank-card {
        background: linear-gradient(135deg, #1a1f2e, #16213e);
        border: 1px solid #00d4aa;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 10px;
    }
    .rank-number {
        font-size: 2rem;
        font-weight: 900;
        color: #00d4aa;
    }
    .rank-match {
        font-size: 1.1rem;
        font-weight: 700;
        color: #ffffff;
    }
    .rank-liga {
        font-size: 0.8rem;
        color: #8892a4;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .badge-edge {
        background: #00d4aa22;
        color: #00d4aa;
        border: 1px solid #00d4aa;
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 0.85rem;
        font-weight: 700;
    }
    .badge-tipo-H { background: #1e3a5f; color: #4da6ff; border: 1px solid #4da6ff; border-radius: 6px; padding: 2px 10px; font-weight: 700; }
    .badge-tipo-D { background: #3a2e1e; color: #ffaa4d; border: 1px solid #ffaa4d; border-radius: 6px; padding: 2px 10px; font-weight: 700; }
    .badge-tipo-A { background: #1e3a2e; color: #4dff9a; border: 1px solid #4dff9a; border-radius: 6px; padding: 2px 10px; font-weight: 700; }
    .metric-box {
        background: #1a1f2e;
        border-radius: 10px;
        padding: 14px;
        text-align: center;
        border: 1px solid #2a2f3e;
    }
    .metric-val { font-size: 1.6rem; font-weight: 900; color: #00d4aa; }
    .metric-lbl { font-size: 0.75rem; color: #8892a4; text-transform: uppercase; letter-spacing: 1px; }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; font-weight: 600; }
    h1 { color: #ffffff !important; }
    .warning-box {
        background: #2a1f1e;
        border: 1px solid #ff6b4d;
        border-radius: 8px;
        padding: 10px 16px;
        color: #ff9980;
        font-size: 0.85rem;
    }
    .info-box {
        background: #1a2a1e;
        border: 1px solid #00d4aa;
        border-radius: 8px;
        padding: 10px 16px;
        color: #80ffcc;
        font-size: 0.85rem;
    }
    .timestamp-box {
        background: #1a1f2e;
        border: 1px solid #2a3a5e;
        border-radius: 8px;
        padding: 8px 14px;
        color: #8892a4;
        font-size: 0.8rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# SESSION STATE — persiste reportes en memoria durante la sesión
# Necesario porque Streamlit Cloud no persiste archivos en disco
# ===============================

if "df_value_bets" not in st.session_state:
    st.session_state.df_value_bets = None
if "df_backtest" not in st.session_state:
    st.session_state.df_backtest = None
if "df_resumen_backtest" not in st.session_state:
    st.session_state.df_resumen_backtest = None

# Intentar cargar desde disco si existe (primera carga o deploy nuevo)
csv_vb = os.path.join(BASE_DIR, "reports", "value_bets.csv")
csv_bt = os.path.join(BASE_DIR, "reports", "backtest_historico.csv")
if st.session_state.df_value_bets is None and os.path.exists(csv_vb):
    try:
        st.session_state.df_value_bets = pd.read_csv(csv_vb)
    except Exception:
        pass
if st.session_state.df_backtest is None and os.path.exists(csv_bt):
    try:
        st.session_state.df_backtest = pd.read_csv(csv_bt)
    except Exception:
        pass

# ===============================
# HEADER
# ===============================

st.markdown("# ⚽ Futbol Quant Bot")
st.markdown("**Sistema de análisis cuantitativo con detección de Value Bets**")

# FIX: mostrar hora actual Argentina en el header
hora_arg_local = datetime.now(timezone.utc) - timedelta(hours=3)
st.markdown(
    f"<div class='timestamp-box'>🕐 Hora Argentina: <b>{hora_arg_local.strftime('%d/%m/%Y %H:%M')}</b> (GMT-3)</div>",
    unsafe_allow_html=True
)
st.divider()

# ===============================
# FUNCION DE RANKING
# ===============================

def calcular_score(row):
    score = row['edge']
    cuota = row['cuota']
    if 1.70 <= cuota <= 3.50:
        score += 3.0
    elif cuota < 1.50 or cuota > 5.00:
        score -= 3.0
    if row['tipo'] == 'D':
        score -= 2.0
    if row['edge'] >= 10:
        score += 2.0
    elif row['edge'] >= 7:
        score += 1.0
    return round(score, 2)


def generar_ranking(df, top_n=15, edge_minimo=5.0, excluir_empates=False):
    df = df.copy()
    df = df[df['edge'] >= edge_minimo]
    if excluir_empates:
        df = df[df['tipo'] != 'D']
    df = df[(df['cuota'] >= 1.30) & (df['cuota'] <= 8.00)]
    if df.empty:
        return df
    df['score'] = df.apply(calcular_score, axis=1)
    df = df.sort_values('score', ascending=False).head(top_n)
    df = df.reset_index(drop=True)
    df.index += 1
    return df


def mostrar_ranking(df_rank):
    tipo_labels = {'H': 'LOCAL', 'D': 'EMPATE', 'A': 'VISITANTE'}
    tipo_clases = {'H': 'badge-tipo-H', 'D': 'badge-tipo-D', 'A': 'badge-tipo-A'}

    for i, row in df_rank.iterrows():
        tipo_label = tipo_labels.get(row['tipo'], row['tipo'])
        tipo_clase = tipo_clases.get(row['tipo'], '')

        # FIX: mostrar fecha y hora ARG si existen en el CSV
        fecha_str = ""
        if 'fecha' in row and pd.notna(row.get('fecha', None)):
            fecha_str = str(row['fecha'])
        hora_str = ""
        if 'hora_arg' in row and pd.notna(row.get('hora_arg', None)):
            hora_str = str(row['hora_arg'])
        elif 'hora' in row and pd.notna(row.get('hora', None)):
            hora_str = str(row['hora'])

        col1, col2, col3, col4 = st.columns([0.5, 3, 1.5, 1.5])

        with col1:
            st.markdown(f"<div class='rank-number'>#{i}</div>", unsafe_allow_html=True)

        with col2:
            fecha_display = f"{fecha_str} · {hora_str}" if hora_str else fecha_str
            st.markdown(f"""
                <div class='rank-liga'>{row['liga']} {f"· 📅 {fecha_display}" if fecha_display else ""}</div>
                <div class='rank-match'>🏠 {row['local']} vs ✈️ {row['visitante']}</div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <span class='{tipo_clase}'>{tipo_label}</span><br><br>
                <span style='color:#8892a4; font-size:0.8rem;'>Cuota: <b style='color:white'>{row['cuota']}</b></span>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
                <span class='badge-edge'>EDGE {row['edge']}%</span><br><br>
                <span style='color:#8892a4; font-size:0.8rem;'>Score: <b style='color:#00d4aa'>{row['score']}</b></span>
            """, unsafe_allow_html=True)

        st.markdown("<hr style='border-color:#1e2535; margin:4px 0'>", unsafe_allow_html=True)


# ===============================
# TABS PRINCIPALES
# ===============================

tab1, tab2, tab3, tab4 = st.tabs(["🏆 Ranking de Apuestas", "📊 Backtesting Histórico", "🔍 Detección en Vivo", "💰 Finanzas"])

# -----------------------------------------------
# TAB 1 — RANKING INTELIGENTE
# FIX: muestra metadata del reporte (cuándo se generó, para qué ventana)
# -----------------------------------------------
with tab1:
    st.subheader("🏆 Ranking inteligente de apuestas")
    st.markdown("Seleccioná los parámetros y el sistema te muestra las mejores oportunidades ordenadas por score compuesto.")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        top_n = st.slider("Cantidad de apuestas a mostrar", min_value=5, max_value=30, value=15, step=5)
    with col_b:
        edge_min = st.slider("Edge mínimo (%)", min_value=3.0, max_value=15.0, value=5.0, step=0.5)
    with col_c:
        excluir_empates = st.checkbox("Excluir empates (tipo D)", value=False)

    # FIX: leer de session_state (persiste aunque el disco se borre)
    df_raw = st.session_state.df_value_bets

    if df_raw is not None and not df_raw.empty:

        # FIX: mostrar contexto temporal del reporte antes del ranking
        if 'generado_en' in df_raw.columns:
            generado = df_raw['generado_en'].iloc[0]
            ventana = df_raw['ventana_horas'].iloc[0] if 'ventana_horas' in df_raw.columns else "?"
            st.markdown(
                f"<div class='info-box'>📋 Reporte generado el <b>{generado}</b> · Ventana: próximas <b>{ventana} horas</b> · {len(df_raw)} oportunidades totales</div>",
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)

            # FIX: advertir si el reporte tiene más de 12 horas
            try:
                gen_dt = datetime.strptime(generado, "%Y-%m-%d %H:%M")
                diff_horas = (datetime.now() - gen_dt).total_seconds() / 3600
                if diff_horas > 12:
                    st.markdown(
                        f"<div class='warning-box'>⚠️ Este reporte tiene <b>{diff_horas:.0f} horas</b> de antigüedad. "
                        f"Ejecutá nuevamente la Detección en Vivo para actualizar.</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown("<br>", unsafe_allow_html=True)
            except Exception:
                pass
        else:
            # CSV sin metadata = generado por versión anterior (backtesting)
            st.markdown(
                "<div class='warning-box'>⚠️ Este reporte no tiene fecha de generación. "
                "Puede contener partidos históricos. Ejecutá la Detección en Vivo para obtener datos actualizados.</div>",
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)

        df_rank = generar_ranking(df_raw, top_n=top_n, edge_minimo=edge_min, excluir_empates=excluir_empates)

        if df_rank.empty:
            st.warning(f"No hay apuestas con edge ≥ {edge_min}%. Probá bajando el filtro.")
        else:
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(f"<div class='metric-box'><div class='metric-val'>{len(df_rank)}</div><div class='metric-lbl'>Apuestas seleccionadas</div></div>", unsafe_allow_html=True)
            with m2:
                st.markdown(f"<div class='metric-box'><div class='metric-val'>{df_rank['edge'].mean():.1f}%</div><div class='metric-lbl'>Edge promedio</div></div>", unsafe_allow_html=True)
            with m3:
                st.markdown(f"<div class='metric-box'><div class='metric-val'>{df_rank['cuota'].mean():.2f}</div><div class='metric-lbl'>Cuota promedio</div></div>", unsafe_allow_html=True)
            with m4:
                ligas_unicas = df_rank['liga'].nunique()
                st.markdown(f"<div class='metric-box'><div class='metric-val'>{ligas_unicas}</div><div class='metric-lbl'>Ligas cubiertas</div></div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            if not excluir_empates and (df_rank['tipo'] == 'D').any():
                st.markdown("<div class='warning-box'>⚠️ El ranking incluye empates (D). Son menos predecibles — considerá activar el filtro si querés mayor consistencia.</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

            mostrar_ranking(df_rank)

            st.divider()
            st.markdown("**📥 Descargar ranking**")
            cols_export = [c for c in df_rank.columns if c not in ['score', 'generado_en', 'ventana_horas']]
            csv_export = df_rank[cols_export].to_csv(index=True).encode('utf-8')
            st.download_button(
                label="Descargar como CSV",
                data=csv_export,
                file_name=f"ranking_value_bets_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

    else:
        st.info("Todavía no hay reporte generado. Ejecutá la Detección en Vivo primero.")
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        **Cómo empezar:**
        1. Ir a la pestaña **🔍 Detección en Vivo**
        2. Elegir la ventana de horas y hacer click en **Ejecutar análisis de mercado**
        3. Volver acá para ver el ranking actualizado
        """)

# -----------------------------------------------
# TAB 2 — BACKTESTING
# FIX: ahora lee backtest_historico.csv (separado de value_bets.csv)
# -----------------------------------------------
with tab2:
    st.subheader("📊 Backtesting histórico por liga")
    st.markdown("Analiza partidos ya jugados para medir la precisión del modelo y el yield histórico.")
    st.markdown(
        "<div class='info-box'>ℹ️ Los datos del backtesting son solo para validar el modelo. "
        "Para apuestas reales, usá la pestaña <b>Detección en Vivo</b>.</div>",
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("▶️ Ejecutar backtesting", key="btn_backtest"):
        try:
            import app
            with st.spinner("Descargando datos y analizando ligas... esto puede tardar unos segundos"):
                apuestas, resumen = app.run()

            if apuestas:
                st.session_state.df_backtest = pd.DataFrame(apuestas)
                st.session_state.df_resumen_backtest = pd.DataFrame(resumen)
                st.success(f"✅ Completado — {len(apuestas)} apuestas históricas analizadas en {len(resumen)} ligas")

                st.subheader("Resumen por liga")
                df_resumen = st.session_state.df_resumen_backtest

                def color_yield(val):
                    color = '#00d4aa' if val > 0 else '#ff6b4d'
                    return f'color: {color}; font-weight: bold'

                st.dataframe(
                    df_resumen.style.map(color_yield, subset=['yield %']),
                    width="stretch"
                )

                st.subheader("Detalle completo de apuestas históricas")
                st.dataframe(st.session_state.df_backtest, width="stretch")

                st.markdown("<div class='warning-box'>⚠️ Argentina, Brasil y MLS pueden mostrar 0 apuestas por falta de cuotas Pinnacle en el dataset.</div>", unsafe_allow_html=True)
            else:
                st.warning("No se detectaron apuestas en ninguna liga.")

        except Exception as e:
            st.error(f"Error en backtesting: {e}")

    # FIX: leer backtest_historico.csv (no value_bets.csv)
    roi_path = os.path.join(BASE_DIR, "reports", "roi_historial.csv")
    backtest_path = os.path.join(BASE_DIR, "reports", "backtest_historico.csv")

    if os.path.exists(roi_path):
        st.divider()
        st.subheader("📈 Historial ROI acumulado")
        df_roi = pd.read_csv(roi_path)
        st.dataframe(df_roi, width="stretch")

    if os.path.exists(backtest_path):
        st.divider()
        st.subheader("📋 Último backtesting guardado")
        df_bt = pd.read_csv(backtest_path)
        if 'generado_en' in df_bt.columns:
            gen = df_bt['generado_en'].iloc[0]
            st.markdown(f"<div class='timestamp-box'>Generado el: <b>{gen}</b> · {len(df_bt)} registros</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df_bt, width="stretch")

# -----------------------------------------------
# TAB 3 — DETECCION EN VIVO
# FIX: slider de ventana temporal + info clara del contexto
# -----------------------------------------------
with tab3:
    st.subheader("🔍 Detección de Value Bets en próximos partidos")
    st.markdown("Busca partidos futuros con cuotas en tiempo real (The Odds API) y detecta oportunidades según el modelo.")

    # FIX: controles de búsqueda antes del botón
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        # FIX: ventana ampliada — antes era fija en 6h, ahora configurable
        horas_ventana = st.slider(
            "⏱️ Buscar partidos en las próximas N horas",
            min_value=6,
            max_value=72,
            value=48,
            step=6,
            help="6h = solo hoy. 48h = mañana incluido. 72h = próximos 3 días."
        )
    with col_h2:
        st.markdown("<br>", unsafe_allow_html=True)
        ahora_arg = datetime.now(timezone.utc) - timedelta(hours=3)
        hasta_arg = ahora_arg + timedelta(hours=horas_ventana)
        st.markdown(
            f"<div class='info-box'>📅 Buscando desde <b>{ahora_arg.strftime('%d/%m %H:%M')}</b> "
            f"hasta <b>{hasta_arg.strftime('%d/%m %H:%M')}</b> (hora ARG)</div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("▶️ Ejecutar análisis de mercado", key="btn_live"):
        try:
            import main
            with st.spinner(f"Analizando mercados en vivo (ventana: {horas_ventana}h)..."):
                apuestas = main.run(horas=horas_ventana)

            if apuestas:
                df_result = pd.DataFrame(apuestas)
                st.session_state.df_value_bets = df_result  # FIX: guardar en session_state
                st.success(f"✅ {len(apuestas)} value bets detectadas para las próximas {horas_ventana}h")
                cols_order = ['liga', 'fecha', 'hora_arg', 'local', 'visitante', 'apuesta', 'cuota', 'prob_modelo', 'prob_impl', 'edge', 'con_stats']
                cols_show = [c for c in cols_order if c in df_result.columns]
                st.dataframe(df_result[cols_show], width="stretch")
            else:
                st.info(
                    f"No se detectaron value bets en las próximas {horas_ventana}h. "
                    "Posibles causas: no hay partidos en esa ventana, la API key no está configurada, "
                    "o los equipos no tienen suficiente historial."
                )

        except Exception as e:
            st.error(f"Error en detección en vivo: {e}")
            if "ODDS_API_KEY" in str(e):
                st.markdown("""
                **Cómo configurar la API key:**
                1. Crear cuenta en [The Odds API](https://the-odds-api.com)
                2. En Streamlit Cloud: Settings → Secrets → agregar `ODDS_API_KEY = "tu_token"`
                """)

    # FIX: mostrar último reporte desde session_state (no depende del disco)
    df_last = st.session_state.df_value_bets
    if df_last is not None and not df_last.empty:
        st.divider()
        st.subheader("📋 Último reporte guardado")

        if 'generado_en' in df_last.columns:
            gen = df_last['generado_en'].iloc[0]
            vent = df_last['ventana_horas'].iloc[0] if 'ventana_horas' in df_last.columns else "?"
            try:
                gen_dt = datetime.strptime(gen, "%Y-%m-%d %H:%M")
                diff_h = (datetime.now() - gen_dt).total_seconds() / 3600
                antiguedad = f"{diff_h:.0f}h de antigüedad"
            except Exception:
                antiguedad = ""
            st.markdown(
                f"<div class='timestamp-box'>Generado: <b>{gen}</b> · Ventana: <b>{vent}h</b> · {antiguedad} · <b>{len(df_last)}</b> registros</div>",
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='warning-box'>⚠️ Reporte sin timestamp — puede contener datos históricos. "
                "Ejecutá el análisis para actualizar.</div>",
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)

        cols_order = ['liga', 'fecha', 'hora_arg', 'local', 'visitante', 'apuesta', 'cuota', 'prob_modelo', 'prob_impl', 'edge', 'con_stats']
        cols_show = [c for c in cols_order if c in df_last.columns]
        st.dataframe(df_last[cols_show] if cols_show else df_last, width="stretch")

# -----------------------------------------------
# TAB 4 — FINANZAS
# Lee y escribe en Google Sheets para historial persistente
# -----------------------------------------------
with tab4:
    st.subheader("💰 Gestión Financiera de Apuestas")
    st.markdown("Registrá tus apuestas, controlá tu bankroll y analizá tu rendimiento histórico.")

    # ===============================
    # CONEXION GOOGLE SHEETS
    # ===============================

    def conectar_sheets():
        """Conecta con Google Sheets usando credenciales de Streamlit Secrets."""
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            # FIX: copiar el dict y reparar la private_key si tiene saltos de línea rotos
            creds_dict = dict(st.secrets["gcp_service_account"])
            pk = creds_dict.get("private_key", "")
            # Si la key tiene \\n literales en vez de \n reales, los convierte
            if "\\n" in pk:
                pk = pk.replace("\\n", "\n")
            # Si la key no tiene saltos de línea en absoluto, los reconstruye
            if "\n" not in pk:
                pk = pk.replace("-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----\n")
                pk = pk.replace("-----END RSA PRIVATE KEY-----", "\n-----END RSA PRIVATE KEY-----\n")
            creds_dict["private_key"] = pk

            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            sheet_id = st.secrets["SHEET_ID"]
            return client.open_by_key(sheet_id)
        except Exception as e:
            st.error(f"Error conectando Google Sheets: {e}")
            return None

    def cargar_apuestas(spreadsheet):
        """Carga el historial de apuestas desde Google Sheets."""
        try:
            hoja = spreadsheet.worksheet("Apuestas")
            data = hoja.get_all_records()
            if data:
                return pd.DataFrame(data)
            else:
                return pd.DataFrame(columns=[
                    "fecha", "liga", "local", "visitante", "apuesta",
                    "cuota", "stake_ars", "resultado", "ganancia_ars", "bankroll_post"
                ])
        except Exception:
            # Si la hoja no existe, crearla con encabezados
            try:
                hoja = spreadsheet.add_worksheet(title="Apuestas", rows=1000, cols=15)
                hoja.append_row([
                    "fecha", "liga", "local", "visitante", "apuesta",
                    "cuota", "stake_ars", "resultado", "ganancia_ars", "bankroll_post"
                ])
                return pd.DataFrame(columns=[
                    "fecha", "liga", "local", "visitante", "apuesta",
                    "cuota", "stake_ars", "resultado", "ganancia_ars", "bankroll_post"
                ])
            except Exception as e2:
                st.error(f"No se pudo crear la hoja: {e2}")
                return pd.DataFrame()

    def guardar_apuesta(spreadsheet, fila):
        """Guarda una nueva apuesta en Google Sheets."""
        try:
            hoja = spreadsheet.worksheet("Apuestas")
            hoja.append_row(fila)
            return True
        except Exception as e:
            st.error(f"Error guardando: {e}")
            return False

    # ===============================
    # KELLY CRITERION
    # ===============================

    def kelly_stake(bankroll, prob, cuota, fraccion=0.5):
        """Calcula el stake recomendado por Kelly Half."""
        b = cuota - 1
        p = prob / 100
        q = 1 - p
        kelly = (b * p - q) / b
        kelly_half = max(0, kelly * fraccion)
        return round(kelly_half * bankroll, 2), round(kelly_half * 100, 2)

    # ===============================
    # CONECTAR Y CARGAR DATOS
    # ===============================

    spreadsheet = conectar_sheets()

    if spreadsheet is None:
        st.markdown("""
        <div class='warning-box'>
        ⚠️ <b>Google Sheets no está configurado todavía.</b><br><br>
        Para activarlo necesitás agregar en Streamlit Cloud → Settings → Secrets:<br><br>
        <code>[gcp_service_account]</code><br>
        <code>type = "service_account"</code><br>
        <code>... (el contenido del JSON que bajaste)</code><br><br>
        <code>SHEET_ID = "el-id-de-tu-planilla"</code>
        </div>
        """, unsafe_allow_html=True)
    else:
        df_fin = cargar_apuestas(spreadsheet)

        # ===============================
        # MÉTRICAS PRINCIPALES
        # ===============================

        if not df_fin.empty and 'ganancia_ars' in df_fin.columns:
            df_fin['ganancia_ars'] = pd.to_numeric(df_fin['ganancia_ars'], errors='coerce').fillna(0)
            df_fin['stake_ars'] = pd.to_numeric(df_fin['stake_ars'], errors='coerce').fillna(0)
            df_fin['cuota'] = pd.to_numeric(df_fin['cuota'], errors='coerce').fillna(0)
            df_fin['bankroll_post'] = pd.to_numeric(df_fin['bankroll_post'], errors='coerce').fillna(0)

            total_apostado = df_fin['stake_ars'].sum()
            ganancia_total = df_fin['ganancia_ars'].sum()
            total_apuestas = len(df_fin)
            ganadas = len(df_fin[df_fin['resultado'] == '✅ Ganada'])
            perdidas = len(df_fin[df_fin['resultado'] == '❌ Perdida'])
            tasa_acierto = (ganadas / total_apuestas * 100) if total_apuestas > 0 else 0
            yield_total = (ganancia_total / total_apostado * 100) if total_apostado > 0 else 0
            bankroll_actual = df_fin['bankroll_post'].iloc[-1] if not df_fin.empty else BANKROLL_ARS

            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3, m4, m5 = st.columns(5)
            with m1:
                color = '#00d4aa' if ganancia_total >= 0 else '#ff6b4d'
                st.markdown(f"<div class='metric-box'><div class='metric-val' style='color:{color}'>$ {ganancia_total:,.0f}</div><div class='metric-lbl'>P&L Total (ARS)</div></div>", unsafe_allow_html=True)
            with m2:
                color = '#00d4aa' if yield_total >= 0 else '#ff6b4d'
                st.markdown(f"<div class='metric-box'><div class='metric-val' style='color:{color}'>{yield_total:.1f}%</div><div class='metric-lbl'>Yield</div></div>", unsafe_allow_html=True)
            with m3:
                st.markdown(f"<div class='metric-box'><div class='metric-val'>{tasa_acierto:.0f}%</div><div class='metric-lbl'>Tasa de Acierto</div></div>", unsafe_allow_html=True)
            with m4:
                st.markdown(f"<div class='metric-box'><div class='metric-val'>{total_apuestas}</div><div class='metric-lbl'>Apuestas ({ganadas}✅ {perdidas}❌)</div></div>", unsafe_allow_html=True)
            with m5:
                st.markdown(f"<div class='metric-box'><div class='metric-val'>$ {bankroll_actual:,.0f}</div><div class='metric-lbl'>Bankroll Actual</div></div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

        # ===============================
        # REGISTRAR NUEVA APUESTA
        # ===============================

        st.divider()
        st.subheader("➕ Registrar nueva apuesta")

        # Calcular bankroll actual
        if not df_fin.empty and 'bankroll_post' in df_fin.columns and len(df_fin) > 0:
            try:
                bankroll_actual = float(df_fin['bankroll_post'].iloc[-1])
            except Exception:
                bankroll_actual = 30000.0
        else:
            bankroll_actual = 30000.0

        col_f1, col_f2 = st.columns(2)

        with col_f1:
            fecha_ap = st.date_input("Fecha", value=datetime.now(timezone.utc).date())
            liga_ap = st.selectbox("Liga", [
                "Premier League", "La Liga", "Serie A", "Bundesliga",
                "Ligue 1", "Eredivisie", "Portugal", "Argentina", "Brasil", "MLS", "Otra"
            ])
            local_ap = st.text_input("Equipo local", placeholder="Ej: Manchester City")
            visitante_ap = st.text_input("Equipo visitante", placeholder="Ej: Arsenal")
            apuesta_ap = st.selectbox("Tipo de apuesta", ["Local", "Empate", "Visitante"])

        with col_f2:
            cuota_ap = st.number_input("Cuota", min_value=1.01, max_value=20.0, value=1.80, step=0.01)
            prob_ap = st.number_input("Probabilidad estimada (%)", min_value=1.0, max_value=99.0, value=55.0, step=0.5)

            # Kelly automático
            kelly_monto, kelly_pct = kelly_stake(bankroll_actual, prob_ap, cuota_ap)
            st.markdown(
                f"<div class='info-box'>🎯 Kelly Half sugiere: <b>$ {kelly_monto:,.0f} ARS</b> ({kelly_pct:.1f}% del bankroll)</div>",
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)

            stake_ap = st.number_input("Stake real (ARS)", min_value=0.0, value=float(kelly_monto), step=100.0)
            resultado_ap = st.selectbox("Resultado", ["⏳ Pendiente", "✅ Ganada", "❌ Perdida"])

        # Calcular ganancia
        if resultado_ap == "✅ Ganada":
            ganancia = round(stake_ap * (cuota_ap - 1), 2)
        elif resultado_ap == "❌ Perdida":
            ganancia = -stake_ap
        else:
            ganancia = 0.0

        bankroll_post = round(bankroll_actual + ganancia, 2)

        if resultado_ap != "⏳ Pendiente":
            color_g = '#00d4aa' if ganancia >= 0 else '#ff6b4d'
            st.markdown(
                f"<div class='metric-box' style='margin-top:12px'>"
                f"<div class='metric-val' style='color:{color_g}'>$ {ganancia:+,.0f}</div>"
                f"<div class='metric-lbl'>Ganancia · Bankroll post: $ {bankroll_post:,.0f}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("💾 Guardar apuesta", key="btn_guardar_apuesta"):
            if not local_ap or not visitante_ap:
                st.warning("Completá al menos los equipos local y visitante.")
            else:
                fila = [
                    str(fecha_ap), liga_ap, local_ap, visitante_ap, apuesta_ap,
                    cuota_ap, stake_ap, resultado_ap, ganancia, bankroll_post
                ]
                ok = guardar_apuesta(spreadsheet, fila)
                if ok:
                    st.success("✅ Apuesta guardada correctamente en Google Sheets.")
                    st.rerun()

        # ===============================
        # ROI POR LIGA
        # ===============================

        if not df_fin.empty and len(df_fin) > 0:
            st.divider()
            st.subheader("📊 Rendimiento por liga")

            df_terminadas = df_fin[df_fin['resultado'] != '⏳ Pendiente'].copy()

            if not df_terminadas.empty:
                resumen_liga = df_terminadas.groupby('liga').agg(
                    apuestas=('stake_ars', 'count'),
                    apostado=('stake_ars', 'sum'),
                    ganancia=('ganancia_ars', 'sum')
                ).reset_index()
                resumen_liga['yield %'] = (resumen_liga['ganancia'] / resumen_liga['apostado'] * 100).round(1)
                resumen_liga['ganadas'] = df_terminadas[df_terminadas['resultado'] == '✅ Ganada'].groupby('liga').size().reindex(resumen_liga['liga']).fillna(0).values
                resumen_liga = resumen_liga.sort_values('yield %', ascending=False)

                def color_yield_fin(val):
                    color = '#00d4aa' if val > 0 else '#ff6b4d'
                    return f'color: {color}; font-weight: bold'

                st.dataframe(
                    resumen_liga.style.map(color_yield_fin, subset=['yield %']),
                    width="stretch"
                )

            # ===============================
            # EVOLUCIÓN DEL BANKROLL
            # ===============================

            st.divider()
            st.subheader("📈 Evolución del bankroll")

            df_evol = df_fin[df_fin['bankroll_post'] > 0].copy()
            if not df_evol.empty:
                import matplotlib.pyplot as plt
                import matplotlib.ticker as mticker

                fig, ax = plt.subplots(figsize=(10, 3))
                fig.patch.set_facecolor('#0e1117')
                ax.set_facecolor('#1a1f2e')

                ax.plot(
                    range(len(df_evol)),
                    df_evol['bankroll_post'].values,
                    color='#00d4aa', linewidth=2, marker='o', markersize=4
                )
                ax.fill_between(
                    range(len(df_evol)),
                    df_evol['bankroll_post'].values,
                    alpha=0.15, color='#00d4aa'
                )
                ax.set_xlabel("Apuesta #", color='#8892a4', fontsize=9)
                ax.set_ylabel("Bankroll (ARS)", color='#8892a4', fontsize=9)
                ax.tick_params(colors='#8892a4')
                ax.spines['bottom'].set_color('#2a2f3e')
                ax.spines['left'].set_color('#2a2f3e')
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

            # ===============================
            # HISTORIAL COMPLETO
            # ===============================

            st.divider()
            st.subheader("📋 Historial completo de apuestas")

            cols_hist = ['fecha', 'liga', 'local', 'visitante', 'apuesta', 'cuota', 'stake_ars', 'resultado', 'ganancia_ars', 'bankroll_post']
            cols_show_hist = [c for c in cols_hist if c in df_fin.columns]
            st.dataframe(df_fin[cols_show_hist].sort_values('fecha', ascending=False) if 'fecha' in df_fin.columns else df_fin[cols_show_hist], width="stretch")

            # Descargar historial
            csv_hist = df_fin[cols_show_hist].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar historial CSV",
                data=csv_hist,
                file_name=f"historial_apuestas_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
