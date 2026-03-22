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
    /* POD tab estilos */
    .pod-señal-fuerte {
        background: #1a3a2e;
        border: 1px solid #4dff9a;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
    }
    .pod-señal-buena {
        background: #1a2a3e;
        border: 1px solid #4da6ff;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
    }
    .pod-metric { font-size: 1.4rem; font-weight: 900; }
    .pod-label  { font-size: 0.72rem; color: #8892a4; text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# ===============================
# SESSION STATE
# ===============================

if "df_value_bets" not in st.session_state:
    st.session_state.df_value_bets = None
if "df_backtest" not in st.session_state:
    st.session_state.df_backtest = None
if "df_resumen_backtest" not in st.session_state:
    st.session_state.df_resumen_backtest = None
if "df_pod" not in st.session_state:
    st.session_state.df_pod = None

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

hora_arg_local = datetime.now(timezone.utc) - timedelta(hours=3)
st.markdown(
    f"<div class='timestamp-box'>🕐 Hora Argentina: <b>{hora_arg_local.strftime('%d/%m/%Y %H:%M')}</b> (GMT-3)</div>",
    unsafe_allow_html=True
)
st.divider()

# ===============================
# FUNCIONES DE RANKING
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
        tipo_clase  = tipo_clases.get(row['tipo'], '')

        fecha_str = str(row['fecha'])   if 'fecha'   in row and pd.notna(row.get('fecha'))   else ""
        hora_str  = str(row['hora_arg']) if 'hora_arg' in row and pd.notna(row.get('hora_arg')) else (
                    str(row['hora'])     if 'hora'    in row and pd.notna(row.get('hora'))    else "")

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
# FUNCIONES POD
# ===============================

import numpy as np

def _detectar_col(df, opciones):
    for op in opciones:
        if op in df.columns:
            return op
    return None

def _normalizar_pod(df_raw):
    MAPA_COLS = {
        "evento":         ["Event","Match","Game","event","match"],
        "fecha":          ["Date","date","Fecha","Event Date"],
        "liga":           ["League","league","Competition","Sport"],
        "mercado":        ["Market","market","Bet Type","bet_type"],
        "seleccion":      ["Selection","selection","Pick","Team"],
        "cuota_apertura": ["Opening Odds","opening_odds","Open","open_odds"],
        "cuota_cierre":   ["Closing Odds","closing_odds","Close","close_odds","Pinnacle Closing"],
        "cuota_apostada": ["Odds","odds","Bet Odds","bet_odds","Your Odds"],
        "stake":          ["Stake","stake","Amount","Wager"],
        "resultado":      ["Result","result","Outcome","outcome","Grade"],
        "ganancia":       ["Profit","profit","P&L","pnl"],
        "clv":            ["CLV","clv","Closing Line Value"],
        "ev":             ["EV","ev","Expected Value"],
    }
    mapa = {}
    for campo, opciones in MAPA_COLS.items():
        col = _detectar_col(df_raw, opciones)
        if col:
            mapa[col] = campo
    df = df_raw.rename(columns=mapa)
    for col_num in ["cuota_apertura","cuota_cierre","cuota_apostada","stake","ganancia","clv","ev"]:
        if col_num in df.columns:
            df[col_num] = pd.to_numeric(df[col_num], errors="coerce")
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", dayfirst=False)
    return df

def _calcular_clv(cuota_apost, cuota_cierre):
    if pd.isna(cuota_apost) or pd.isna(cuota_cierre) or cuota_cierre <= 0:
        return np.nan
    return round((cuota_apost / cuota_cierre - 1) * 100, 2)

def _ev_apuesta(prob, cuota):
    return round((prob * (cuota - 1)) - (1 - prob), 4)

def _kelly_half(prob, cuota):
    if cuota <= 1: return 0
    b = cuota - 1
    k = (prob * b - (1 - prob)) / b
    return round(max(0, k * 0.5), 4)

def _clasificar(ev_pct, clv):
    if ev_pct > 8 and (pd.isna(clv) or clv > 3):  return "🔥 FUERTE"
    elif ev_pct > 5 and (pd.isna(clv) or clv >= 0): return "✅ BUENA"
    elif ev_pct > 3:                                 return "⚠️ MARGINAL"
    else:                                            return "❌ DESCARTAR"

def analizar_pod(archivo, bankroll, unidad):
    """Procesa el CSV de POD y devuelve df analizado + resumen + mensajes Telegram."""
    try:
        df_raw = pd.read_csv(archivo)
    except Exception as e:
        return None, {}, []

    df = _normalizar_pod(df_raw)

    if "cuota_apostada" not in df.columns:
        return None, {"error": f"Columnas no reconocidas: {list(df_raw.columns)}"}, []

    # CLV
    if "clv" not in df.columns or df["clv"].isna().all():
        if "cuota_cierre" in df.columns:
            df["clv"] = df.apply(lambda r: _calcular_clv(r["cuota_apostada"], r["cuota_cierre"]), axis=1)
        else:
            df["clv"] = np.nan

    # Prob Pinnacle y EV
    if "cuota_cierre" in df.columns:
        df["prob_pinnacle"] = df["cuota_cierre"].apply(lambda c: (1/c)/1.02 if pd.notna(c) and c > 1 else np.nan)
    else:
        df["prob_pinnacle"] = np.nan

    if "ev" not in df.columns or df["ev"].isna().all():
        df["ev"] = df.apply(
            lambda r: _ev_apuesta(r["prob_pinnacle"], r["cuota_apostada"])
            if pd.notna(r.get("prob_pinnacle")) and pd.notna(r.get("cuota_apostada")) else np.nan,
            axis=1
        )
    df["ev_pct"] = df["ev"].apply(lambda x: round(x*100, 2) if pd.notna(x) else np.nan)

    # Kelly + Stake
    df["kelly_half"] = df.apply(
        lambda r: _kelly_half(r.get("prob_pinnacle") or 0.5, r["cuota_apostada"])
        if pd.notna(r.get("cuota_apostada")) else 0, axis=1
    )
    df["stake_ars"]      = df["kelly_half"].apply(lambda k: round(k * bankroll))
    df["stake_unidades"] = df["kelly_half"].apply(lambda k: round(k * bankroll / unidad, 2))

    # Clasificación
    df["señal"] = df.apply(
        lambda r: _clasificar(r.get("ev_pct") or 0, r.get("clv")), axis=1
    )

    # Backtest si hay resultado
    res_map = {"won":True,"win":True,"w":True,"1":True,"lost":False,"loss":False,"l":False,"0":False}
    if "resultado" in df.columns:
        df["gano"] = df["resultado"].apply(lambda x: res_map.get(str(x).lower().strip(), np.nan))
        df_res = df[df["gano"].notna()].copy()
        if len(df_res) > 0:
            ganadas  = int(df_res["gano"].sum())
            win_rate = ganadas / len(df_res)
            if "ganancia" in df_res.columns and df_res["ganancia"].notna().any():
                pnl = df_res["ganancia"].sum()
            else:
                pnl = df_res.apply(
                    lambda r: (r["cuota_apostada"]-1)*unidad if r["gano"] else -unidad, axis=1
                ).sum()
            roi = pnl / (len(df_res) * unidad) * 100
        else:
            ganadas = 0; win_rate = 0; pnl = 0; roi = 0
    else:
        ganadas = 0; win_rate = 0; pnl = 0; roi = 0; df_res = pd.DataFrame()

    resumen = {
        "total":          len(df),
        "fuertes":        int((df["señal"]=="🔥 FUERTE").sum()),
        "buenas":         int((df["señal"]=="✅ BUENA").sum()),
        "marginales":     int((df["señal"]=="⚠️ MARGINAL").sum()),
        "descartadas":    int((df["señal"]=="❌ DESCARTAR").sum()),
        "clv_prom":       round(df["clv"].mean(), 2) if df["clv"].notna().any() else "N/A",
        "ev_prom":        round(df["ev_pct"].mean(), 2) if df["ev_pct"].notna().any() else "N/A",
        "apuestas_hist":  len(df_res) if len(df_res) > 0 else 0,
        "ganadas":        ganadas,
        "win_rate":       f"{win_rate:.1%}" if win_rate else "N/A",
        "roi":            f"{roi:.2f}%" if roi else "N/A",
        "pnl_ars":        f"${pnl:,.0f}" if pnl else "N/A",
    }

    # Mensajes Telegram
    msgs = []
    df_act = df[df["señal"].isin(["🔥 FUERTE","✅ BUENA"])].copy()
    for _, r in df_act.iterrows():
        ev_str  = f"{r['ev_pct']:.1f}%" if pd.notna(r.get("ev_pct")) else "N/A"
        clv_str = f"{r['clv']:.1f}%"    if pd.notna(r.get("clv"))    else "N/A"
        fecha_s = r["fecha"].strftime("%d/%m %H:%M") if pd.notna(r.get("fecha")) and hasattr(r["fecha"],"strftime") else str(r.get("fecha","?"))
        msgs.append(
            f"{r['señal']} VALUE BET\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 {fecha_s}\n"
            f"🏆 {r.get('liga','?')}\n"
            f"⚽ {r.get('evento','?')}\n"
            f"🎯 {r.get('mercado','?')}: {r.get('seleccion','?')}\n"
            f"💰 Cuota: {r.get('cuota_apostada','?')}\n"
            f"📊 EV: {ev_str}  |  CLV: {clv_str}\n"
            f"🧮 Kelly Half: {r['kelly_half']*100:.1f}%\n"
            f"💵 Stake: ${r['stake_ars']:,.0f} ARS  ({r['stake_unidades']:.1f}u)\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    return df, resumen, msgs


def enviar_telegram_pod(mensajes):
    import requests
    token   = st.secrets.get("TELEGRAM_TOKEN", os.getenv("TELEGRAM_TOKEN",""))
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID","5976165080"))
    if not token:
        st.error("❌ TELEGRAM_TOKEN no configurado en Streamlit Secrets.")
        return
    ok = 0
    for msg in mensajes:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg},
                timeout=5
            )
            if r.status_code == 200:
                ok += 1
        except Exception as e:
            st.warning(f"Error Telegram: {e}")
    st.success(f"✅ {ok}/{len(mensajes)} mensajes enviados a Telegram")


# ===============================
# TABS PRINCIPALES  ← AGREGADO tab5 POD
# ===============================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 Ranking de Apuestas",
    "📊 Backtesting Histórico",
    "🔍 Detección en Vivo",
    "💰 Finanzas",
    "📡 POD — Pinnacle Signals"
])

# -----------------------------------------------
# TAB 1 — RANKING
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

    df_raw = st.session_state.df_value_bets

    if df_raw is not None and not df_raw.empty:
        if 'generado_en' in df_raw.columns:
            generado = df_raw['generado_en'].iloc[0]
            ventana  = df_raw['ventana_horas'].iloc[0] if 'ventana_horas' in df_raw.columns else "?"
            st.markdown(
                f"<div class='info-box'>📋 Reporte generado el <b>{generado}</b> · Ventana: próximas <b>{ventana} horas</b> · {len(df_raw)} oportunidades totales</div>",
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)
            try:
                gen_dt   = datetime.strptime(generado, "%Y-%m-%d %H:%M")
                diff_h   = (datetime.now() - gen_dt).total_seconds() / 3600
                if diff_h > 12:
                    st.markdown(
                        f"<div class='warning-box'>⚠️ Este reporte tiene <b>{diff_h:.0f} horas</b> de antigüedad. Ejecutá la Detección en Vivo para actualizar.</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown("<br>", unsafe_allow_html=True)
            except Exception:
                pass
        else:
            st.markdown(
                "<div class='warning-box'>⚠️ Reporte sin fecha. Puede contener partidos históricos. Ejecutá la Detección en Vivo.</div>",
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
                st.markdown(f"<div class='metric-box'><div class='metric-val'>{df_rank['liga'].nunique()}</div><div class='metric-lbl'>Ligas cubiertas</div></div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            if not excluir_empates and (df_rank['tipo'] == 'D').any():
                st.markdown("<div class='warning-box'>⚠️ El ranking incluye empates (D). Considerá activar el filtro.</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

            mostrar_ranking(df_rank)

            st.divider()
            cols_export = [c for c in df_rank.columns if c not in ['score','generado_en','ventana_horas']]
            csv_export  = df_rank[cols_export].to_csv(index=True).encode('utf-8')
            st.download_button("⬇️ Descargar ranking CSV", data=csv_export,
                               file_name=f"ranking_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")
    else:
        st.info("Todavía no hay reporte. Ejecutá la Detección en Vivo primero.")

# -----------------------------------------------
# TAB 2 — BACKTESTING
# -----------------------------------------------
with tab2:
    st.subheader("📊 Backtesting histórico por liga")
    st.markdown("Analiza partidos ya jugados para medir la precisión del modelo y el yield histórico.")
    st.markdown("<div class='info-box'>ℹ️ Solo para validar el modelo. Para apuestas reales usá la Detección en Vivo.</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("▶️ Ejecutar backtesting", key="btn_backtest"):
        try:
            import app
            with st.spinner("Descargando datos y analizando ligas..."):
                apuestas, resumen = app.run()
            if apuestas:
                st.session_state.df_backtest         = pd.DataFrame(apuestas)
                st.session_state.df_resumen_backtest = pd.DataFrame(resumen)
                st.success(f"✅ {len(apuestas)} apuestas históricas en {len(resumen)} ligas")

                def color_yield(val):
                    return f'color: {"#00d4aa" if val > 0 else "#ff6b4d"}; font-weight: bold'

                st.subheader("Resumen por liga")
                st.dataframe(st.session_state.df_resumen_backtest.style.map(color_yield, subset=['yield %']), width="stretch")
                st.subheader("Detalle completo")
                st.dataframe(st.session_state.df_backtest, width="stretch")
                st.markdown("<div class='warning-box'>⚠️ ARG, BRA y MLS pueden mostrar 0 apuestas por falta de cuotas Pinnacle.</div>", unsafe_allow_html=True)
            else:
                st.warning("No se detectaron apuestas en ninguna liga.")
        except Exception as e:
            st.error(f"Error en backtesting: {e}")

    roi_path      = os.path.join(BASE_DIR, "reports", "roi_historial.csv")
    backtest_path = os.path.join(BASE_DIR, "reports", "backtest_historico.csv")
    if os.path.exists(roi_path):
        st.divider()
        st.subheader("📈 Historial ROI acumulado")
        st.dataframe(pd.read_csv(roi_path), width="stretch")
    if os.path.exists(backtest_path):
        st.divider()
        st.subheader("📋 Último backtesting guardado")
        df_bt = pd.read_csv(backtest_path)
        if 'generado_en' in df_bt.columns:
            st.markdown(f"<div class='timestamp-box'>Generado: <b>{df_bt['generado_en'].iloc[0]}</b> · {len(df_bt)} registros</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df_bt, width="stretch")

# -----------------------------------------------
# TAB 3 — DETECCION EN VIVO
# -----------------------------------------------
with tab3:
    st.subheader("🔍 Detección de Value Bets en próximos partidos")

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        horas_ventana = st.slider("⏱️ Buscar partidos en las próximas N horas", min_value=6, max_value=72, value=48, step=6)
    with col_h2:
        st.markdown("<br>", unsafe_allow_html=True)
        ahora_arg = datetime.now(timezone.utc) - timedelta(hours=3)
        hasta_arg = ahora_arg + timedelta(hours=horas_ventana)
        st.markdown(
            f"<div class='info-box'>📅 Desde <b>{ahora_arg.strftime('%d/%m %H:%M')}</b> hasta <b>{hasta_arg.strftime('%d/%m %H:%M')}</b> (ARG)</div>",
            unsafe_allow_html=True
        )
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("▶️ Ejecutar análisis de mercado", key="btn_live"):
        try:
            import main
            with st.spinner(f"Analizando mercados en vivo ({horas_ventana}h)..."):
                apuestas = main.run(horas=horas_ventana)
            if apuestas:
                df_result = pd.DataFrame(apuestas)
                st.session_state.df_value_bets = df_result
                st.success(f"✅ {len(apuestas)} value bets detectadas")
                cols_order = ['liga','fecha','hora_arg','local','visitante','apuesta','cuota','prob_modelo','prob_impl','edge','con_stats']
                cols_show  = [c for c in cols_order if c in df_result.columns]
                st.dataframe(df_result[cols_show], width="stretch")
            else:
                st.info("No se detectaron value bets. Verificá la API key o ampliá la ventana horaria.")
        except Exception as e:
            st.error(f"Error: {e}")
            if "ODDS_API_KEY" in str(e):
                st.markdown("**Configurar API key:** Streamlit Cloud → Settings → Secrets → `ODDS_API_KEY = 'tu_token'`")

    df_last = st.session_state.df_value_bets
    if df_last is not None and not df_last.empty:
        st.divider()
        st.subheader("📋 Último reporte")
        if 'generado_en' in df_last.columns:
            gen  = df_last['generado_en'].iloc[0]
            vent = df_last['ventana_horas'].iloc[0] if 'ventana_horas' in df_last.columns else "?"
            st.markdown(f"<div class='timestamp-box'>Generado: <b>{gen}</b> · Ventana: <b>{vent}h</b> · <b>{len(df_last)}</b> registros</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
        cols_order = ['liga','fecha','hora_arg','local','visitante','apuesta','cuota','prob_modelo','prob_impl','edge','con_stats']
        cols_show  = [c for c in cols_order if c in df_last.columns]
        st.dataframe(df_last[cols_show], width="stretch")
        csv_dl = df_last.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Descargar CSV", data=csv_dl,
                           file_name=f"value_bets_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")

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

            creds_dict = dict(st.secrets["gcp_service_account"])
            pk = creds_dict.get("private_key", "")
            if "\\n" in pk:
                pk = pk.replace("\\n", "\n")
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

        if not df_fin.empty and 'ganancia_ars' in df_fin.columns:
            df_fin['ganancia_ars']   = pd.to_numeric(df_fin['ganancia_ars'],   errors='coerce').fillna(0)
            df_fin['stake_ars']      = pd.to_numeric(df_fin['stake_ars'],      errors='coerce').fillna(0)
            df_fin['cuota']          = pd.to_numeric(df_fin['cuota'],          errors='coerce').fillna(0)
            df_fin['bankroll_post']  = pd.to_numeric(df_fin['bankroll_post'],  errors='coerce').fillna(0)

            total_apostado = df_fin['stake_ars'].sum()
            ganancia_total = df_fin['ganancia_ars'].sum()
            total_apuestas = len(df_fin)
            ganadas        = len(df_fin[df_fin['resultado'] == '✅ Ganada'])
            perdidas       = len(df_fin[df_fin['resultado'] == '❌ Perdida'])
            tasa_acierto   = (ganadas / total_apuestas * 100) if total_apuestas > 0 else 0
            yield_total    = (ganancia_total / total_apostado * 100) if total_apostado > 0 else 0
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

        st.divider()
        st.subheader("➕ Registrar nueva apuesta")

        if not df_fin.empty and 'bankroll_post' in df_fin.columns and len(df_fin) > 0:
            try:
                bankroll_actual = float(df_fin['bankroll_post'].iloc[-1])
            except Exception:
                bankroll_actual = 30000.0
        else:
            bankroll_actual = 30000.0

        col_f1, col_f2 = st.columns(2)

        with col_f1:
            fecha_ap     = st.date_input("Fecha", value=datetime.now(timezone.utc).date())
            liga_ap      = st.selectbox("Liga", [
                "Premier League","La Liga","Serie A","Bundesliga",
                "Ligue 1","Eredivisie","Portugal","Argentina","Brasil","MLS","Otra"
            ])
            local_ap     = st.text_input("Equipo local",     placeholder="Ej: Manchester City")
            visitante_ap = st.text_input("Equipo visitante", placeholder="Ej: Arsenal")
            apuesta_ap   = st.selectbox("Tipo de apuesta", ["Local","Empate","Visitante"])

        with col_f2:
            cuota_ap = st.number_input("Cuota", min_value=1.01, max_value=20.0, value=1.80, step=0.01)
            prob_ap  = st.number_input("Probabilidad estimada (%)", min_value=1.0, max_value=99.0, value=55.0, step=0.5)

            kelly_monto, kelly_pct = kelly_stake(bankroll_actual, prob_ap, cuota_ap)
            st.markdown(
                f"<div class='info-box'>🎯 Kelly Half sugiere: <b>$ {kelly_monto:,.0f} ARS</b> ({kelly_pct:.1f}% del bankroll)</div>",
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)

            stake_ap     = st.number_input("Stake real (ARS)", min_value=0.0, value=float(kelly_monto), step=100.0)
            resultado_ap = st.selectbox("Resultado", ["⏳ Pendiente","✅ Ganada","❌ Perdida"])

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

                st.dataframe(resumen_liga.style.map(color_yield_fin, subset=['yield %']), width="stretch")

            st.divider()
            st.subheader("📈 Evolución del bankroll")
            df_evol = df_fin[df_fin['bankroll_post'] > 0].copy()
            if not df_evol.empty:
                import matplotlib.pyplot as plt
                import matplotlib.ticker as mticker
                fig, ax = plt.subplots(figsize=(10, 3))
                fig.patch.set_facecolor('#0e1117')
                ax.set_facecolor('#1a1f2e')
                ax.plot(range(len(df_evol)), df_evol['bankroll_post'].values,
                        color='#00d4aa', linewidth=2, marker='o', markersize=4)
                ax.fill_between(range(len(df_evol)), df_evol['bankroll_post'].values,
                                alpha=0.15, color='#00d4aa')
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

            st.divider()
            st.subheader("📋 Historial completo de apuestas")
            cols_hist      = ['fecha','liga','local','visitante','apuesta','cuota','stake_ars','resultado','ganancia_ars','bankroll_post']
            cols_show_hist = [c for c in cols_hist if c in df_fin.columns]
            st.dataframe(
                df_fin[cols_show_hist].sort_values('fecha', ascending=False) if 'fecha' in df_fin.columns else df_fin[cols_show_hist],
                width="stretch"
            )
            csv_hist = df_fin[cols_show_hist].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar historial CSV",
                data=csv_hist,
                file_name=f"historial_apuestas_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# -----------------------------------------------
# TAB 5 — POD  ← NUEVO
# -----------------------------------------------
with tab5:
    st.subheader("📡 Pinnacle Odds Dropper — Análisis de Señales Sharp")

    st.markdown("""
    <div class='info-box'>
    <b>Flujo de uso:</b><br>
    1. En POD → <i>Bet Tracker → Export → CSV</i><br>
    2. Subí el archivo acá abajo<br>
    3. El sistema calcula EV real, CLV, Kelly Half y genera alertas Telegram
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        bankroll_pod = st.number_input("💰 Bankroll (ARS)", value=30000, step=1000, min_value=1000, key="pod_bank")
    with col_p2:
        unidad_pod   = st.number_input("📏 Valor 1 unidad (ARS)", value=300, step=100, min_value=100, key="pod_unit")
    with col_p3:
        umbral_ev_pod = st.slider("🎯 EV mínimo (%)", min_value=1, max_value=15, value=5, key="pod_ev")

    archivo_pod = st.file_uploader("📁 Subí el CSV exportado de POD", type=["csv"], key="pod_upload")

    if archivo_pod:
        with st.spinner("Analizando señales POD..."):
            df_pod, resumen_pod, msgs_pod = analizar_pod(archivo_pod, bankroll_pod, unidad_pod)

        if df_pod is None:
            st.error(f"❌ No se pudo leer el CSV. {resumen_pod.get('error','Verificá el formato.')}")
        else:
            st.session_state.df_pod = df_pod

            # ── Métricas ──
            st.subheader("📊 Resumen del período")
            c1,c2,c3,c4,c5,c6 = st.columns(6)
            c1.markdown(f"<div class='metric-box'><div class='metric-val pod-metric'>{resumen_pod['total']}</div><div class='pod-label'>Total señales</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-box'><div class='metric-val pod-metric' style='color:#4dff9a'>{resumen_pod['fuertes']}</div><div class='pod-label'>🔥 Fuertes</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-box'><div class='metric-val pod-metric' style='color:#4da6ff'>{resumen_pod['buenas']}</div><div class='pod-label'>✅ Buenas</div></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='metric-box'><div class='metric-val pod-metric'>{resumen_pod['clv_prom']}%</div><div class='pod-label'>CLV prom</div></div>", unsafe_allow_html=True)
            c5.markdown(f"<div class='metric-box'><div class='metric-val pod-metric'>{resumen_pod['win_rate']}</div><div class='pod-label'>Win Rate</div></div>", unsafe_allow_html=True)
            c6.markdown(f"<div class='metric-box'><div class='metric-val pod-metric'>{resumen_pod['roi']}</div><div class='pod-label'>ROI</div></div>", unsafe_allow_html=True)

            st.markdown(f"<br><div class='metric-box' style='text-align:left; display:inline-block; padding:8px 16px'>"
                        f"P&L histórico: <b style='color:#00d4aa'>{resumen_pod['pnl_ars']}</b> &nbsp;|&nbsp; "
                        f"Apuestas con resultado: <b>{resumen_pod['apuestas_hist']}</b> &nbsp;|&nbsp; "
                        f"Ganadas: <b>{resumen_pod['ganadas']}</b>"
                        f"</div>", unsafe_allow_html=True)

            # ── Value Bets accionables ──
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("🎯 Value Bets Accionables")

            df_act = df_pod[df_pod["señal"].isin(["🔥 FUERTE","✅ BUENA"]) & (df_pod.get("ev_pct", pd.Series([0]*len(df_pod))) >= umbral_ev_pod)].copy()

            if df_act.empty:
                st.warning(f"No hay value bets con EV ≥ {umbral_ev_pod}% en este dataset.")
            else:
                for _, r in df_act.iterrows():
                    es_fuerte = "FUERTE" in r["señal"]
                    clase = "pod-señal-fuerte" if es_fuerte else "pod-señal-buena"
                    ev_s  = f"{r['ev_pct']:.1f}%"  if pd.notna(r.get("ev_pct"))  else "N/A"
                    clv_s = f"{r['clv']:.1f}%"      if pd.notna(r.get("clv"))     else "N/A"
                    fecha_s = r["fecha"].strftime("%d/%m %H:%M") if pd.notna(r.get("fecha")) and hasattr(r["fecha"],"strftime") else str(r.get("fecha","?"))
                    st.markdown(f"""
                    <div class='{clase}'>
                      <span style='font-size:1.1rem; font-weight:700; color:white'>
                        {r.get('señal','')} &nbsp; {r.get('evento','?')}
                      </span><br>
                      <span style='color:#8892a4; font-size:0.8rem'>{r.get('liga','?')} · {fecha_s}</span><br><br>
                      <span style='color:#8892a4'>Mercado:</span> <b style='color:white'>{r.get('mercado','?')} — {r.get('seleccion','?')}</b>
                      &nbsp;&nbsp;
                      <span style='color:#8892a4'>Cuota:</span> <b style='color:#00d4aa'>{r.get('cuota_apostada','?')}</b>
                      &nbsp;&nbsp;
                      <span style='color:#8892a4'>EV:</span> <b style='color:#4dff9a'>{ev_s}</b>
                      &nbsp;&nbsp;
                      <span style='color:#8892a4'>CLV:</span> <b style='color:#4da6ff'>{clv_s}</b>
                      &nbsp;&nbsp;
                      <span style='color:#8892a4'>Kelly½:</span> <b style='color:white'>{r['kelly_half']*100:.1f}%</b>
                      &nbsp;&nbsp;
                      <span style='color:#8892a4'>Stake:</span> <b style='color:#ffaa4d'>${r['stake_ars']:,.0f} ARS ({r['stake_unidades']:.1f}u)</b>
                    </div>
                    """, unsafe_allow_html=True)

            # ── Mensajes Telegram ──
            if msgs_pod:
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("📱 Alertas Telegram")
                with st.expander(f"Ver {len(msgs_pod)} mensajes listos para enviar"):
                    for msg in msgs_pod:
                        st.code(msg, language="")

                if st.button("📤 Enviar todas las alertas a Telegram", key="pod_tg"):
                    enviar_telegram_pod(msgs_pod)

            # ── Tabla completa ──
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("📋 Ver dataset completo analizado"):
                cols_show = [c for c in ["fecha","liga","evento","mercado","seleccion",
                                          "cuota_apostada","ev_pct","clv","kelly_half",
                                          "stake_unidades","señal","resultado"] if c in df_pod.columns]
                st.dataframe(df_pod[cols_show], use_container_width=True)

            # ── Descarga ──
            st.download_button(
                "⬇️ Descargar análisis completo (CSV)",
                data=df_pod.to_csv(index=False).encode("utf-8"),
                file_name=f"pod_analisis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

    else:
        st.markdown("""
        <div class='warning-box'>
        ⬆️ Subí el CSV de POD para comenzar.<br><br>
        <b>¿Cómo exportar desde POD?</b><br>
        Bet Tracker → botón <i>Export</i> → CSV → guardar → subir acá.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**📊 Clasificación de señales:**")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.markdown("<div class='metric-box'><b style='color:#4dff9a'>🔥 FUERTE</b><br><span class='pod-label'>EV > 8% y CLV > 3%</span></div>", unsafe_allow_html=True)
        col_s2.markdown("<div class='metric-box'><b style='color:#4da6ff'>✅ BUENA</b><br><span class='pod-label'>EV > 5% y CLV ≥ 0%</span></div>", unsafe_allow_html=True)
        col_s3.markdown("<div class='metric-box'><b style='color:#ffaa4d'>⚠️ MARGINAL</b><br><span class='pod-label'>EV > 3%</span></div>", unsafe_allow_html=True)
        col_s4.markdown("<div class='metric-box'><b style='color:#ff6b4d'>❌ DESCARTAR</b><br><span class='pod-label'>EV ≤ 3%</span></div>", unsafe_allow_html=True)
