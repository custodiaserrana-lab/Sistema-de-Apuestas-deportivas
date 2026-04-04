"""
╔══════════════════════════════════════════════════════════════╗
║         FUTBOL QUANT BOT — Dashboard v2.0                   ║
║         Custodia Serrana Lab © 2026                         ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
import os
import logging
import yaml
from datetime import datetime, timedelta, timezone
import time

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Futbol Quant Bot",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    background-color: #0a0e1a !important;
    color: #e8eaf0 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}

/* ── Header ── */
.main-header {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3.2rem;
    letter-spacing: 0.12em;
    background: linear-gradient(135deg, #00ff88 0%, #00ccff 50%, #ff6b35 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
    margin-bottom: 0;
}

.sub-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #4a5568;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-top: 4px;
}

/* ── Metric cards ── */
.metric-card {
    background: linear-gradient(135deg, #111827 0%, #1a2035 100%);
    border: 1px solid #1e2d40;
    border-radius: 12px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00ff88, #00ccff);
}
.metric-value {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.4rem;
    color: #00ff88;
    line-height: 1;
}
.metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: #4a5568;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    margin-top: 4px;
}

/* ── Bet cards ── */
.bet-card {
    background: #111827;
    border: 1px solid #1e2d40;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
    position: relative;
    transition: border-color 0.2s;
}
.bet-card:hover { border-color: #00ff8855; }
.bet-card-hot {
    border-left: 3px solid #ff6b35;
}
.bet-card-warm {
    border-left: 3px solid #00ccff;
}
.bet-card-std {
    border-left: 3px solid #00ff88;
}
.bet-teams {
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    color: #e8eaf0;
}
.bet-meta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: #4a6785;
    margin-top: 2px;
}
.bet-edge {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.6rem;
    color: #ff6b35;
}
.bet-odds {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.1rem;
    color: #00ccff;
    font-weight: 600;
}
.bet-type-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
}
.badge-H { background: #00ff8820; color: #00ff88; border: 1px solid #00ff8840; }
.badge-D { background: #ffcc0020; color: #ffcc00; border: 1px solid #ffcc0040; }
.badge-A { background: #ff6b3520; color: #ff6b35; border: 1px solid #ff6b3540; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #070b14 !important;
    border-right: 1px solid #1e2d40 !important;
}
[data-testid="stSidebar"] .stButton button {
    width: 100%;
    background: linear-gradient(135deg, #00ff88, #00ccff);
    color: #0a0e1a;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.1rem;
    letter-spacing: 0.1em;
    border: none;
    border-radius: 8px;
    padding: 12px;
    cursor: pointer;
}

/* ── DataFrames ── */
.stDataFrame { border: 1px solid #1e2d40 !important; border-radius: 10px !important; }
thead tr th { background: #111827 !important; color: #00ff88 !important;
              font-family: 'IBM Plex Mono', monospace !important; font-size: 0.72rem !important; }

/* ── Tabs ── */
[data-baseweb="tab-list"] { background: #111827 !important; border-radius: 10px; padding: 4px; }
[data-baseweb="tab"] { font-family: 'IBM Plex Mono', monospace !important; font-size: 0.78rem !important; }

/* ── Status chips ── */
.status-live { color: #ff4444; font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem;
               animation: blink 1s infinite; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

/* ── Divider ── */
.q-divider { border: none; border-top: 1px solid #1e2d40; margin: 20px 0; }

/* ── No results ── */
.no-results {
    text-align: center;
    padding: 60px;
    color: #2d3748;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    letter-spacing: 0.1em;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════

EDGE_MINIMO_DEFAULT = 3.0

LIGAS_ODDS_API = {
    "Premier_League": "soccer_epl",
    "La_Liga":        "soccer_spain_la_liga",
    "Serie_A":        "soccer_italy_serie_a",
    "Bundesliga":     "soccer_germany_bundesliga",
    "Ligue_1":        "soccer_france_ligue_one",
    "Eredivisie":     "soccer_netherlands_eredivisie",
    "Portugal":       "soccer_portugal_primeira_liga",
    "Argentina":      "soccer_argentina_primera_division",
    "Brasil":         "soccer_brazil_campeonato",
    "MLS":            "soccer_usa_mls",
}

LIGAS_STATS = {
    "Premier_League": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "La_Liga":        "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "Serie_A":        "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    "Bundesliga":     "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
    "Ligue_1":        "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
    "Eredivisie":     "https://www.football-data.co.uk/mmz4281/2526/N1.csv",
    "Portugal":       "https://www.football-data.co.uk/mmz4281/2526/P1.csv",
    "Argentina":      "https://www.football-data.co.uk/new/ARG.csv",
    "Brasil":         "https://www.football-data.co.uk/new/BRA.csv",
    "MLS":            "https://www.football-data.co.uk/new/USA.csv",
}

LIGA_FLAGS = {
    "Premier_League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "La_Liga":        "🇪🇸",
    "Serie_A":        "🇮🇹",
    "Bundesliga":     "🇩🇪",
    "Ligue_1":        "🇫🇷",
    "Eredivisie":     "🇳🇱",
    "Portugal":       "🇵🇹",
    "Argentina":      "🇦🇷",
    "Brasil":         "🇧🇷",
    "MLS":            "🇺🇸",
}

# ══════════════════════════════════════════════════════════════
# FUNCIONES CORE (importadas de main.py / app.py)
# ══════════════════════════════════════════════════════════════

def normalizar_columnas(df):
    renombres = {}
    if 'Home' in df.columns and 'HomeTeam' not in df.columns: renombres['Home'] = 'HomeTeam'
    if 'Away' in df.columns and 'AwayTeam' not in df.columns: renombres['Away'] = 'AwayTeam'
    if 'HG'   in df.columns and 'FTHG'    not in df.columns: renombres['HG']   = 'FTHG'
    if 'AG'   in df.columns and 'FTAG'    not in df.columns: renombres['AG']   = 'FTAG'
    if 'Res'  in df.columns and 'FTR'     not in df.columns: renombres['Res']  = 'FTR'
    if 'PSCH'   in df.columns and 'PSH'   not in df.columns: renombres['PSCH']   = 'PSH'
    if 'PSCD'   in df.columns and 'PSD'   not in df.columns: renombres['PSCD']   = 'PSD'
    if 'PSCA'   in df.columns and 'PSA'   not in df.columns: renombres['PSCA']   = 'PSA'
    if 'PH' in df.columns and 'PSH' not in df.columns: renombres['PH'] = 'PSH'
    if 'PD' in df.columns and 'PSD' not in df.columns: renombres['PD'] = 'PSD'
    if 'PA' in df.columns and 'PSA' not in df.columns: renombres['PA'] = 'PSA'
    if 'MaxCH'  in df.columns and 'MaxH'  not in df.columns: renombres['MaxCH']  = 'MaxH'
    if 'MaxCD'  in df.columns and 'MaxD'  not in df.columns: renombres['MaxCD']  = 'MaxD'
    if 'MaxCA'  in df.columns and 'MaxA'  not in df.columns: renombres['MaxCA']  = 'MaxA'
    if 'AvgCH'  in df.columns and 'AvgH'  not in df.columns: renombres['AvgCH']  = 'AvgH'
    if 'AvgCD'  in df.columns and 'AvgD'  not in df.columns: renombres['AvgCD']  = 'AvgD'
    if 'AvgCA'  in df.columns and 'AvgA'  not in df.columns: renombres['AvgCA']  = 'AvgA'
    if 'B365CH' in df.columns and 'B365H' not in df.columns: renombres['B365CH'] = 'B365H'
    if 'B365CD' in df.columns and 'B365D' not in df.columns: renombres['B365CD'] = 'B365D'
    if 'B365CA' in df.columns and 'B365A' not in df.columns: renombres['B365CA'] = 'B365A'
    if renombres:
        df = df.rename(columns=renombres)
    return df


def motor_probabilidades(x):
    p_L = 1.56 * x + 46.47
    p_V = 0.03 * (x**2) - 1.27 * x + 23.65
    p_E = -0.03 * (x**2) - 0.29 * x + 29.48
    return p_L, p_E, p_V


def kelly_fraction(prob_modelo, cuota, bankroll=30000, unidades=100):
    """Kelly Criterion: fracción óptima y unidades a apostar."""
    p = prob_modelo / 100
    b = cuota - 1
    q = 1 - p
    f = (b * p - q) / b if b > 0 else 0
    f = max(0, min(f, 0.05))          # Cap al 5% del bankroll
    valor_unidad = bankroll / unidades
    stake_ars = f * bankroll
    stake_unidades = stake_ars / valor_unidad
    return round(f * 100, 2), round(stake_ars, 0), round(stake_unidades, 1)


@st.cache_data(ttl=1800, show_spinner=False)
def calcular_ratings_liga(url_csv):
    try:
        r = requests.get(url_csv, timeout=12)
        try:
            df = pd.read_csv(StringIO(r.text), encoding='utf-8-sig')
        except Exception:
            df = pd.read_csv(StringIO(r.text), encoding='latin1')
    except Exception as e:
        return {}, str(e)

    df = normalizar_columnas(df)
    requeridas = ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
    if any(c not in df.columns for c in requeridas):
        return {}, f"Cols faltantes: {[c for c in requeridas if c not in df.columns]}"

    df = df.dropna(subset=['FTR', 'FTHG', 'FTAG'])
    historial = {}
    for _, row in df.iterrows():
        h, a = row['HomeTeam'], row['AwayTeam']
        if h not in historial: historial[h] = []
        if a not in historial: historial[a] = []
        try:
            historial[h].append(float(row['FTHG']) - float(row['FTAG']))
            historial[a].append(float(row['FTAG']) - float(row['FTHG']))
        except (ValueError, TypeError):
            continue

    ratings = {}
    for eq, hist in historial.items():
        u6 = hist[-6:]
        if len(u6) >= 3:
            ratings[eq] = sum(u6)
    return ratings, None


def normalizar_nombre(nombre):
    reemplazos = {
        "FC": "", "CF": "", "AC": "", "SC": "", "AS": "",
        "United": "Utd", "Athletic Club": "Athletic Bilbao",
        "Atlético": "Atletico", "Internazionale": "Inter",
        "Hellas Verona": "Verona",
        "Argentinos Juniors": "Argentinos Jrs",
        "Estudiantes de La Plata": "Estudiantes L.P.",
        "Gimnasia La Plata": "Gimnasia LP",
        "Atletico Mineiro": "Atletico MG",
        "Atletico Paranaense": "Atletico PR",
    }
    nombre = nombre.strip()
    for k, v in reemplazos.items():
        nombre = nombre.replace(k, v)
    return nombre.strip().lower()


def buscar_rating(nombre, ratings):
    n = normalizar_nombre(nombre)
    for eq, r in ratings.items():
        if normalizar_nombre(eq) == n:
            return r
    for eq, r in ratings.items():
        eq_n = normalizar_nombre(eq)
        if n in eq_n or eq_n in n:
            return r
    return None


def extraer_cuotas(partido):
    bookmakers = partido.get("bookmakers", [])
    if not bookmakers:
        return None
    preferidos = ["pinnacle", "betfair_ex_eu", "sport888", "williamhill"]
    mercado = None
    for pref in preferidos:
        for bk in bookmakers:
            if bk["key"] == pref:
                for m in bk.get("markets", []):
                    if m["key"] == "h2h":
                        mercado = m
                        break
            if mercado: break
        if mercado: break
    if not mercado:
        for bk in bookmakers:
            for m in bk.get("markets", []):
                if m["key"] == "h2h":
                    mercado = m
                    break
            if mercado: break
    if not mercado:
        return None
    outcomes = {o["name"]: o["price"] for o in mercado.get("outcomes", [])}
    ch = outcomes.get(partido["home_team"])
    ca = outcomes.get(partido["away_team"])
    cd = outcomes.get("Draw")
    if not all([ch, ca, cd]):
        return None
    return ch, cd, ca


@st.cache_data(ttl=900, show_spinner=False)
def obtener_partidos_odds_api(sport_key, api_key, horas=48):
    ahora = datetime.now(timezone.utc)
    hasta = ahora + timedelta(hours=horas)
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        "apiKey": api_key, "regions": "eu", "markets": "h2h",
        "oddsFormat": "decimal",
        "commenceTimeFrom": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commenceTimeTo":   hasta.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code == 200:
            return r.json(), None
        return [], f"HTTP {r.status_code}"
    except Exception as e:
        return [], str(e)


def analizar_liga_completa(nombre, sport_key, url_stats, api_key, horas, edge_min):
    partidos, err_api = obtener_partidos_odds_api(sport_key, api_key, horas)
    if err_api:
        return [], err_api

    ratings, err_csv = calcular_ratings_liga(url_stats)

    apuestas = []
    for partido in partidos:
        home  = partido["home_team"]
        away  = partido["away_team"]
        comm  = partido.get("commence_time", "")
        try:
            dt_utc = datetime.strptime(comm, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            dt_arg = dt_utc - timedelta(hours=3)
            hora_arg = dt_arg.strftime("%d/%m %H:%M")
            fecha_p  = dt_arg.strftime("%Y-%m-%d")
        except Exception:
            hora_arg = comm
            fecha_p  = ""

        cuotas = extraer_cuotas(partido)
        if not cuotas:
            continue
        ch, cd, ca = cuotas

        rh = buscar_rating(home, ratings)
        ra = buscar_rating(away, ratings)
        x  = (rh if rh is not None else 0) - (ra if ra is not None else 0)
        p_L, p_E, p_V = motor_probabilidades(x)
        tiene_stats = rh is not None and ra is not None

        for tipo, p_m, cuota, label in [("H", p_L, ch, "Local"), ("D", p_E, cd, "Empate"), ("A", p_V, ca, "Visit.")]:
            if cuota <= 1.0: continue
            p_impl = 100 / cuota
            edge   = p_m - p_impl
            if edge >= edge_min:
                f_k, stake_ars, stake_u = kelly_fraction(p_m, cuota)
                apuestas.append({
                    "🏳": LIGA_FLAGS.get(nombre, "⚽"),
                    "Liga":        nombre.replace("_", " "),
                    "Fecha ARG":   hora_arg,
                    "Partido":     f"{home} vs {away}",
                    "Local":       home,
                    "Visitante":   away,
                    "Tipo":        tipo,
                    "Apuesta":     label,
                    "Cuota":       round(cuota, 2),
                    "% Modelo":    round(p_m, 1),
                    "% Impl":      round(p_impl, 1),
                    "Edge %":      round(edge, 2),
                    "Kelly %":     f_k,
                    "Stake ARS":   stake_ars,
                    "Stake U":     stake_u,
                    "Stats":       "✅" if tiene_stats else "⚠️",
                    "_fecha_sort": fecha_p,
                    "_edge_raw":   edge,
                })
    return apuestas, None


# ════════════════════════════════════════════════════════════════
# BACKTESTING ENGINE (de app.py)
# ════════════════════════════════════════════════════════════════

LIGAS_BACKTEST = {
    "Premier_League":   "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "La_Liga":          "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "Serie_A":          "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    "Bundesliga":       "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
    "Ligue_1":          "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
    "Eredivisie":       "https://www.football-data.co.uk/mmz4281/2526/N1.csv",
    "Portugal":         "https://www.football-data.co.uk/mmz4281/2526/P1.csv",
    "Argentina":        "https://www.football-data.co.uk/new/ARG.csv",
    "Brasil":           "https://www.football-data.co.uk/new/BRA.csv",
    "MLS":              "https://www.football-data.co.uk/new/USA.csv",
}


@st.cache_data(ttl=3600, show_spinner=False)
def ejecutar_backtesting_liga(url_csv, nombre_liga, edge_min=3.0):
    try:
        r = requests.get(url_csv, timeout=12)
        try:
            df = pd.read_csv(StringIO(r.text), encoding='utf-8-sig')
        except Exception:
            df = pd.read_csv(StringIO(r.text), encoding='latin1')
    except Exception as e:
        return {}, 0, [], str(e)

    df = normalizar_columnas(df)
    cols_base = ['FTR', 'FTHG', 'FTAG', 'HomeTeam', 'AwayTeam', 'Date']
    if any(c not in df.columns for c in cols_base):
        return {}, 0, [], f"cols faltantes"

    # Detectar cuotas
    for par in [('PSH','PSD','PSA'), ('BbAvH','BbAvD','BbAvA'),
                ('AvgH','AvgD','AvgA'), ('MaxH','MaxD','MaxA'), ('B365H','B365D','B365A')]:
        if all(c in df.columns for c in par):
            col_h, col_d, col_a = par
            break
    else:
        return {}, 0, [], "sin columnas de cuotas"

    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date'])
    hoy = pd.Timestamp.now().normalize()
    df_hist = df[df['Date'] < hoy].dropna(subset=['FTR', col_h, col_d, col_a, 'FTHG', 'FTAG'])

    # Construir ratings
    eq_goles = {}
    for _, row in df_hist.iterrows():
        h, a = row['HomeTeam'], row['AwayTeam']
        if h not in eq_goles: eq_goles[h] = []
        if a not in eq_goles: eq_goles[a] = []
        try:
            eq_goles[h].append(float(row['FTHG']) - float(row['FTAG']))
            eq_goles[a].append(float(row['FTAG']) - float(row['FTHG']))
        except (ValueError, TypeError):
            continue

    stats = {'apuestas': 0, 'ganadoras': 0, 'p_l': 0}
    registros = []

    for _, row in df_hist.iterrows():
        h, a = row['HomeTeam'], row['AwayTeam']
        if len(eq_goles.get(h, [])) < 6 or len(eq_goles.get(a, [])) < 6:
            continue
        x = sum(eq_goles[h][-6:]) - sum(eq_goles[a][-6:])
        p_L, p_E, p_V = motor_probabilidades(x)
        for tipo, p_m, cuota_raw in [('H', p_L, row[col_h]), ('D', p_E, row[col_d]), ('A', p_V, row[col_a])]:
            try:
                cuota = float(cuota_raw)
            except (ValueError, TypeError):
                continue
            edge = p_m - (100 / cuota)
            if edge >= edge_min:
                ganada = (row['FTR'] == tipo)
                pl = (2 * (cuota - 1)) if ganada else -2
                stats['apuestas'] += 1
                stats['p_l'] += pl
                if ganada: stats['ganadoras'] += 1
                registros.append({
                    "Liga":    nombre_liga.replace("_", " "),
                    "Fecha":   row['Date'].strftime("%Y-%m-%d"),
                    "Partido": f"{h} vs {a}",
                    "Tipo":    tipo,
                    "Cuota":   round(cuota, 2),
                    "Prob %":  round(p_m, 1),
                    "Edge %":  round(edge, 2),
                    "P&L":     round(pl, 2),
                    "Res":     "✅" if ganada else "❌",
                })

    yield_neto = 0
    if stats['apuestas'] > 0:
        yield_neto = (stats['p_l'] / (stats['apuestas'] * 2)) * 100

    return stats, yield_neto, registros, None


# ════════════════════════════════════════════════════════════════
# UI HELPERS
# ════════════════════════════════════════════════════════════════

def render_metric(label, value, delta=None):
    delta_html = f'<div style="font-size:0.7rem;color:#4a6785;margin-top:4px">{delta}</div>' if delta else ''
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def tipo_badge(tipo):
    return f'<span class="bet-type-badge badge-{tipo}">{tipo}</span>'


def edge_class(edge):
    if edge >= 10: return "bet-card-hot"
    if edge >= 6:  return "bet-card-warm"
    return "bet-card-std"


def render_bet_card(ap):
    css_class = edge_class(ap["_edge_raw"])
    badge = tipo_badge(ap["Tipo"])
    stats_icon = ap["Stats"]
    st.markdown(f"""
    <div class="bet-card {css_class}">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div class="bet-teams">{ap['🏳']} {ap['Partido']}</div>
                <div class="bet-meta">{ap['Liga']} · {ap['Fecha ARG']} ARG · {stats_icon} stats</div>
                <div style="margin-top:8px">{badge} &nbsp; <span style="color:#8899aa;font-size:0.78rem">{ap['Apuesta']}</span></div>
            </div>
            <div style="text-align:right">
                <div class="bet-edge">+{ap['Edge %']}%</div>
                <div class="bet-odds">{ap['Cuota']}</div>
                <div class="bet-meta">Kelly {ap['Kelly %']}% · {ap['Stake U']}u · ${int(ap['Stake ARS']):,} ARS</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:16px 0 8px">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;
                    background:linear-gradient(135deg,#00ff88,#00ccff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;letter-spacing:0.1em;">
            ⚽ FUTBOL QUANT
        </div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;
                    color:#2d4a3e;letter-spacing:0.3em;">CUSTODIA SERRANA LAB</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # API Key
    api_key_input = ""
    try:
        api_key_input = st.secrets.get("ODDS_API_KEY", "")
    except Exception:
        pass

    if not api_key_input:
        api_key_input = st.text_input(
            "🔑 The Odds API Key",
            type="password",
            placeholder="Tu API key...",
            help="Consíguela en the-odds-api.com"
        )

    st.markdown("---")
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.65rem;color:#2d4a3e;letter-spacing:0.2em;">PARÁMETROS</div>', unsafe_allow_html=True)

    horas_ventana = st.slider("⏱ Ventana (horas)", 6, 72, 48, 6)
    edge_minimo   = st.slider("📐 Edge mínimo %", 1.0, 15.0, 3.0, 0.5)
    bankroll      = st.number_input("💰 Bankroll ARS", value=30000, step=1000)

    ligas_sel = st.multiselect(
        "🌍 Ligas",
        options=list(LIGAS_ODDS_API.keys()),
        default=list(LIGAS_ODDS_API.keys()),
        format_func=lambda x: f"{LIGA_FLAGS.get(x,'⚽')} {x.replace('_',' ')}"
    )

    st.markdown("---")
    scan_live = st.button("🔍 ESCANEAR MERCADOS", use_container_width=True)
    scan_back = st.button("📊 BACKTESTING", use_container_width=True)

    st.markdown("---")
    ts_arg = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
    st.markdown(f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.6rem;color:#2d4a3e;text-align:center">{ts_arg} ARG</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# HEADER PRINCIPAL
# ════════════════════════════════════════════════════════════════

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('<div class="main-header">FUTBOL QUANT BOT</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Sistema de Value Betting Cuantitativo · Custodia Serrana Lab © 2026</div>', unsafe_allow_html=True)
with col_h2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:12px">
        <span class="status-live">● LIVE</span>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;color:#2d4a3e;margin-top:4px">
            {len(ligas_sel)} ligas activas
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr class='q-divider'>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# TABS PRINCIPALES
# ════════════════════════════════════════════════════════════════

tab_live, tab_back, tab_info = st.tabs(["⚡ VALUE BETS LIVE", "📊 BACKTESTING", "ℹ️ SISTEMA"])


# ── TAB 1: LIVE VALUE BETS ─────────────────────────────────────
with tab_live:

    if scan_live or st.session_state.get("vb_data") is not None:

        if scan_live:
            if not api_key_input:
                st.error("⚠️ Ingresá tu API key de The Odds API en el sidebar.")
                st.stop()

            todas_apuestas = []
            errores = []

            prog_bar = st.progress(0)
            status_txt = st.empty()

            for i, nombre in enumerate(ligas_sel):
                sport_key = LIGAS_ODDS_API[nombre]
                url_stats = LIGAS_STATS.get(nombre, "")
                status_txt.markdown(f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.75rem;color:#00ff88">⟳ Escaneando {LIGA_FLAGS.get(nombre,"")} {nombre.replace("_"," ")}...</div>', unsafe_allow_html=True)

                apuestas, err = analizar_liga_completa(
                    nombre, sport_key, url_stats, api_key_input, horas_ventana, edge_minimo
                )
                if err:
                    errores.append(f"{nombre}: {err}")
                todas_apuestas.extend(apuestas)
                prog_bar.progress((i + 1) / len(ligas_sel))

            prog_bar.empty()
            status_txt.empty()
            st.session_state["vb_data"] = todas_apuestas
            st.session_state["vb_errores"] = errores

        datos = st.session_state.get("vb_data", [])
        errores = st.session_state.get("vb_errores", [])

        if errores:
            with st.expander("⚠️ Advertencias"):
                for e in errores:
                    st.caption(e)

        if not datos:
            st.markdown('<div class="no-results">⊘ SIN VALUE BETS EN LA VENTANA SELECCIONADA<br><span style="font-size:0.6rem">Probá ampliar la ventana horaria o reducir el edge mínimo</span></div>', unsafe_allow_html=True)
        else:
            # ── Métricas resumen ──
            df_vb = pd.DataFrame(datos)
            total_bets   = len(df_vb)
            edge_prom    = df_vb["_edge_raw"].mean()
            cuota_prom   = df_vb["Cuota"].mean()
            ligas_con_vb = df_vb["Liga"].nunique()

            c1, c2, c3, c4 = st.columns(4)
            with c1: render_metric("VALUE BETS", str(total_bets), f"en {horas_ventana}h")
            with c2: render_metric("EDGE PROM", f"{edge_prom:.1f}%", "vs mercado")
            with c3: render_metric("CUOTA PROM", f"{cuota_prom:.2f}", "decimal")
            with c4: render_metric("LIGAS", str(ligas_con_vb), "activas")

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Filtros inline ──
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                tipo_filter = st.multiselect("Tipo", ["H","D","A"], default=["H","D","A"])
            with col_f2:
                liga_filter = st.multiselect("Liga", sorted(df_vb["Liga"].unique()), default=sorted(df_vb["Liga"].unique()))
            with col_f3:
                orden = st.selectbox("Ordenar por", ["Edge % ↓", "Cuota ↑", "Fecha ↑"])

            df_fil = df_vb[df_vb["Tipo"].isin(tipo_filter) & df_vb["Liga"].isin(liga_filter)]

            if orden == "Edge % ↓":
                df_fil = df_fil.sort_values("_edge_raw", ascending=False)
            elif orden == "Cuota ↑":
                df_fil = df_fil.sort_values("Cuota", ascending=True)
            else:
                df_fil = df_fil.sort_values("_fecha_sort", ascending=True)

            # ── Vista cards ──
            view_mode = st.radio("Vista", ["Cards", "Tabla"], horizontal=True, label_visibility="collapsed")

            if view_mode == "Cards":
                for _, row in df_fil.iterrows():
                    render_bet_card(row)
            else:
                cols_tabla = ["🏳","Liga","Fecha ARG","Partido","Tipo","Cuota","% Modelo","% Impl","Edge %","Kelly %","Stake U","Stake ARS","Stats"]
                st.dataframe(
                    df_fil[cols_tabla].reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )

            # ── Descarga ──
            csv_out = df_fil[["Liga","Fecha ARG","Partido","Tipo","Apuesta","Cuota","% Modelo","% Impl","Edge %","Kelly %","Stake ARS","Stake U","Stats"]].to_csv(index=False)
            st.download_button(
                "⬇️ Descargar CSV",
                data=csv_out,
                file_name=f"value_bets_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

    else:
        st.markdown("""
        <div class="no-results">
            ⚡ LISTO PARA ESCANEAR<br>
            <span style="font-size:0.6rem">Configurá los parámetros y presioná ESCANEAR MERCADOS</span>
        </div>
        """, unsafe_allow_html=True)


# ── TAB 2: BACKTESTING ─────────────────────────────────────────
with tab_back:

    if scan_back or st.session_state.get("bt_data") is not None:

        if scan_back:
            ligas_bt = ligas_sel if ligas_sel else list(LIGAS_BACKTEST.keys())
            todos_registros = []
            resumen_ligas   = []

            prog = st.progress(0)
            stat = st.empty()

            for i, nombre in enumerate(ligas_bt):
                url = LIGAS_BACKTEST.get(nombre, "")
                if not url:
                    continue
                stat.markdown(f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.75rem;color:#00ccff">⟳ Backtesting {nombre.replace("_"," ")}...</div>', unsafe_allow_html=True)
                stats, yield_n, registros, err = ejecutar_backtesting_liga(url, nombre, edge_minimo)

                if err:
                    resumen_ligas.append({"Liga": nombre.replace("_"," "), "Apuestas": 0, "Yield %": 0, "P&L u": 0, "Estado": f"⚠️ {err}"})
                else:
                    acc = (stats['ganadoras'] / stats['apuestas'] * 100) if stats['apuestas'] > 0 else 0
                    resumen_ligas.append({
                        "Liga":      nombre.replace("_"," "),
                        "Apuestas":  stats['apuestas'],
                        "Ganadoras": stats.get('ganadoras', 0),
                        "Acc %":     round(acc, 1),
                        "Yield %":   round(yield_n, 2),
                        "P&L u":     round(stats['p_l'], 2),
                        "Estado":    "✅" if yield_n > 0 else "🔴"
                    })
                    todos_registros.extend(registros)
                prog.progress((i + 1) / len(ligas_bt))

            prog.empty()
            stat.empty()
            st.session_state["bt_data"] = todos_registros
            st.session_state["bt_resumen"] = resumen_ligas

        registros = st.session_state.get("bt_data", [])
        resumen   = st.session_state.get("bt_resumen", [])

        if resumen:
            df_res = pd.DataFrame(resumen)

            # ── KPIs globales ──
            total_ap = df_res["Apuestas"].sum()
            pl_total = df_res["P&L u"].sum()
            ligas_ok = (df_res["Yield %"] > 0).sum()
            yield_gl = (pl_total / (total_ap * 2) * 100) if total_ap > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            with c1: render_metric("APUESTAS HIST.", str(int(total_ap)))
            with c2: render_metric("YIELD GLOBAL", f"{yield_gl:.1f}%", "P&L global")
            with c3: render_metric("P&L UNIDADES", f"{pl_total:+.1f}u")
            with c4: render_metric("LIGAS +EV", f"{ligas_ok}/{len(df_res)}")

            st.markdown("<br>", unsafe_allow_html=True)

            # Tabla resumen
            st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.72rem;color:#4a6785;letter-spacing:0.2em;margin-bottom:8px">RESUMEN POR LIGA</div>', unsafe_allow_html=True)

            def color_yield(val):
                if isinstance(val, float):
                    color = "#00ff88" if val > 0 else "#ff4444"
                    return f"color: {color}"
                return ""

            st.dataframe(
                df_res.style.applymap(color_yield, subset=["Yield %", "P&L u"]),
                use_container_width=True,
                hide_index=True
            )

        if registros:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.72rem;color:#4a6785;letter-spacing:0.2em;margin-bottom:8px">DETALLE DE APUESTAS</div>', unsafe_allow_html=True)

            df_det = pd.DataFrame(registros)

            # Filtro rápido
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                res_filter = st.multiselect("Resultado", ["✅","❌"], default=["✅","❌"])
            with col_f2:
                liga_filter_bt = st.multiselect("Liga", sorted(df_det["Liga"].unique()), default=sorted(df_det["Liga"].unique()))

            df_det_fil = df_det[df_det["Res"].isin(res_filter) & df_det["Liga"].isin(liga_filter_bt)]

            def color_res(val):
                if val == "✅": return "color: #00ff88"
                if val == "❌": return "color: #ff4444"
                return ""

            st.dataframe(
                df_det_fil.style.applymap(color_res, subset=["Res"]),
                use_container_width=True,
                hide_index=True
            )

            csv_bt = df_det_fil.to_csv(index=False)
            st.download_button("⬇️ Descargar Backtest CSV", csv_bt,
                               f"backtest_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

    else:
        st.markdown('<div class="no-results">📊 BACKTESTING HISTÓRICO<br><span style="font-size:0.6rem">Presioná BACKTESTING en el sidebar para ejecutar</span></div>', unsafe_allow_html=True)


# ── TAB 3: INFO SISTEMA ────────────────────────────────────────
with tab_info:
    col_i1, col_i2 = st.columns(2)

    with col_i1:
        st.markdown("""
        <div class="metric-card">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.3rem;color:#00ff88;letter-spacing:0.1em;margin-bottom:12px">MOTOR MATEMÁTICO</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.78rem;color:#8899aa;line-height:1.9">
            <b style="color:#e8eaf0">P(Local)</b> = 1.56x + 46.47<br>
            <b style="color:#e8eaf0">P(Empate)</b> = -0.03x² - 0.29x + 29.48<br>
            <b style="color:#e8eaf0">P(Visitante)</b> = 0.03x² - 1.27x + 23.65<br><br>
            <b style="color:#00ccff">x</b> = Σ(goles L-V) últimos 6 partidos<br>
            <b style="color:#00ccff">Edge</b> = P(modelo) - P(implícita mercado)<br>
            <b style="color:#ff6b35">Kelly</b> = (b·p - q) / b · bankroll<br>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_i2:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.3rem;color:#00ccff;letter-spacing:0.1em;margin-bottom:12px">CONFIGURACIÓN ACTIVA</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.78rem;color:#8899aa;line-height:1.9">
            <b style="color:#e8eaf0">Bankroll</b>: ${bankroll:,} ARS<br>
            <b style="color:#e8eaf0">Edge mínimo</b>: {edge_minimo}%<br>
            <b style="color:#e8eaf0">Ventana</b>: {horas_ventana}h<br>
            <b style="color:#e8eaf0">Ligas activas</b>: {len(ligas_sel)}<br>
            <b style="color:#e8eaf0">Fuente stats</b>: football-data.co.uk<br>
            <b style="color:#e8eaf0">Fuente cuotas</b>: The Odds API (Pinnacle)<br>
            <b style="color:#e8eaf0">Timezone</b>: GMT-3 (Argentina)<br>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;color:#2d3748;text-align:center;padding:20px">
        FUTBOL QUANT BOT · Custodia Serrana Lab © 2026 · Solo para análisis cuantitativo<br>
        Las apuestas deportivas implican riesgo. Apostá con responsabilidad.
    </div>
    """, unsafe_allow_html=True)
