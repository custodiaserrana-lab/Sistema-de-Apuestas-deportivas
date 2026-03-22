import pandas as pd
import numpy as np
import requests
from io import StringIO
import os
import logging
import yaml
from datetime import datetime, timedelta, timezone

# ===============================
# RUTAS BASE
# ===============================
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR    = os.path.join(BASE_DIR, "logs")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CONFIG_DIR  = os.path.join(BASE_DIR, "config")

os.makedirs(LOGS_DIR,    exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# ===============================
# CONFIGURACION GLOBAL
# ===============================
EDGE_MINIMO = 3.0
fecha = datetime.now().strftime("%Y-%m-%d")

logging.basicConfig(
    filename=os.path.join(LOGS_DIR, f"log_{fecha}.txt"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ===============================
# API KEY — The Odds API
# ===============================
import streamlit as st

def get_api_key():
    try:
        return st.secrets["ODDS_API_KEY"]
    except Exception:
        return os.environ.get("ODDS_API_KEY", "")

# ===============================
# LIGAS — mapeo football-data ↔ The Odds API
# ===============================
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

# ===============================
# FIX CLAVE: NORMALIZAR COLUMNAS
# ARG/BRA usan Home/Away/HG/AG/Res y odds con sufijo C (AvgCH, PSCH, etc.)
# Esta función unifica al formato estándar antes de procesar.
# ===============================

def normalizar_columnas(df):
    renombres = {}
    # Equipos y goles
    if 'Home' in df.columns and 'HomeTeam' not in df.columns: renombres['Home'] = 'HomeTeam'
    if 'Away' in df.columns and 'AwayTeam' not in df.columns: renombres['Away'] = 'AwayTeam'
    if 'HG'   in df.columns and 'FTHG'    not in df.columns: renombres['HG']   = 'FTHG'
    if 'AG'   in df.columns and 'FTAG'    not in df.columns: renombres['AG']   = 'FTAG'
    if 'Res'  in df.columns and 'FTR'     not in df.columns: renombres['Res']  = 'FTR'
    # Odds Pinnacle formato "C" → estándar
    if 'PSCH'   in df.columns and 'PSH'   not in df.columns: renombres['PSCH']   = 'PSH'
    if 'PSCD'   in df.columns and 'PSD'   not in df.columns: renombres['PSCD']   = 'PSD'
    if 'PSCA'   in df.columns and 'PSA'   not in df.columns: renombres['PSCA']   = 'PSA'
    # Odds Max formato "C" → estándar
    if 'MaxCH'  in df.columns and 'MaxH'  not in df.columns: renombres['MaxCH']  = 'MaxH'
    if 'MaxCD'  in df.columns and 'MaxD'  not in df.columns: renombres['MaxCD']  = 'MaxD'
    if 'MaxCA'  in df.columns and 'MaxA'  not in df.columns: renombres['MaxCA']  = 'MaxA'
    # Odds Avg formato "C" → estándar
    if 'AvgCH'  in df.columns and 'AvgH'  not in df.columns: renombres['AvgCH']  = 'AvgH'
    if 'AvgCD'  in df.columns and 'AvgD'  not in df.columns: renombres['AvgCD']  = 'AvgD'
    if 'AvgCA'  in df.columns and 'AvgA'  not in df.columns: renombres['AvgCA']  = 'AvgA'
    # Odds B365 formato "C" → estándar
    if 'B365CH' in df.columns and 'B365H' not in df.columns: renombres['B365CH'] = 'B365H'
    if 'B365CD' in df.columns and 'B365D' not in df.columns: renombres['B365CD'] = 'B365D'
    if 'B365CA' in df.columns and 'B365A' not in df.columns: renombres['B365CA'] = 'B365A'
    if renombres:
        df = df.rename(columns=renombres)
        logging.info(f"Columnas normalizadas: {renombres}")
    return df

# ===============================
# MOTOR MATEMATICO
# ===============================

def motor_probabilidades(x):
    p_L = 1.56 * x + 46.47
    p_V = 0.03 * (x**2) - 1.27 * x + 23.65
    p_E = -0.03 * (x**2) - 0.29 * x + 29.48
    return p_L, p_E, p_V

# ===============================
# CALCULAR RATING DESDE HISTORICO
# FIX: normalizar columnas antes de validar
# ===============================

def calcular_ratings_liga(url_csv):
    """
    Descarga el CSV histórico y calcula el rating de cada equipo
    en sus últimos 6 partidos jugados.
    FIX: normaliza columnas de ARG/BRA antes de procesar.
    """
    try:
        response = requests.get(url_csv, timeout=10)
        # FIX: encoding utf-8-sig elimina el BOM (ï»¿) de los CSV extra
        try:
            df = pd.read_csv(StringIO(response.text), encoding='utf-8-sig')
        except Exception:
            df = pd.read_csv(StringIO(response.text), encoding='latin1')
    except Exception as e:
        logging.error(f"Error descargando stats: {e}")
        return {}

    # FIX: normalizar ANTES de validar columnas
    df = normalizar_columnas(df)

    columnas_requeridas = ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        logging.warning(f"Columnas faltantes tras normalizar: {faltantes}")
        logging.warning(f"Columnas disponibles: {list(df.columns)[:15]}")
        return {}

    # Solo partidos ya jugados con resultado confirmado
    df = df.dropna(subset=['FTR', 'FTHG', 'FTAG'])

    equipos_historial = {}
    for _, fila in df.iterrows():
        h = fila['HomeTeam']
        a = fila['AwayTeam']
        if h not in equipos_historial: equipos_historial[h] = []
        if a not in equipos_historial: equipos_historial[a] = []
        try:
            equipos_historial[h].append(float(fila['FTHG']) - float(fila['FTAG']))
            equipos_historial[a].append(float(fila['FTAG']) - float(fila['FTHG']))
        except (ValueError, TypeError):
            continue

    ratings = {}
    for equipo, historial in equipos_historial.items():
        ultimos_6 = historial[-6:]
        if len(ultimos_6) >= 3:
            ratings[equipo] = sum(ultimos_6)

    logging.info(f"Ratings calculados: {len(ratings)} equipos")
    return ratings

# ===============================
# OBTENER PARTIDOS PROXIMOS — The Odds API
# ===============================

def obtener_partidos_con_cuotas(sport_key, api_key, horas=48):
    ahora = datetime.now(timezone.utc)
    hasta = ahora + timedelta(hours=horas)

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        "apiKey":           api_key,
        "regions":          "eu",
        "markets":          "h2h",
        "oddsFormat":       "decimal",
        "commenceTimeFrom": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commenceTimeTo":   hasta.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 401:
            logging.error("API key inválida o sin permisos")
            return []
        if response.status_code == 429:
            logging.error("Límite de requests alcanzado en The Odds API")
            return []
        if response.status_code != 200:
            logging.error(f"Error {response.status_code} en The Odds API: {sport_key}")
            return []
        partidos = response.json()
        logging.info(f"{sport_key}: {len(partidos)} partidos en próximas {horas}h")
        return partidos
    except Exception as e:
        logging.error(f"Excepción consultando The Odds API ({sport_key}): {e}")
        return []

# ===============================
# EXTRAER CUOTAS PINNACLE
# ===============================

def extraer_cuotas_pinnacle(partido):
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
            if mercado:
                break
        if mercado:
            break

    if not mercado:
        for bk in bookmakers:
            for m in bk.get("markets", []):
                if m["key"] == "h2h":
                    mercado = m
                    break
            if mercado:
                break

    if not mercado:
        return None

    outcomes  = {o["name"]: o["price"] for o in mercado.get("outcomes", [])}
    home_team = partido["home_team"]
    away_team = partido["away_team"]
    cuota_h   = outcomes.get(home_team)
    cuota_a   = outcomes.get(away_team)
    cuota_d   = outcomes.get("Draw")

    if not cuota_h or not cuota_a or not cuota_d:
        return None

    return cuota_h, cuota_d, cuota_a

# ===============================
# NORMALIZAR NOMBRE DE EQUIPO
# FIX: expansiones para equipos ARG/BRA más comunes
# ===============================

def normalizar_nombre(nombre):
    reemplazos = {
        "FC": "", "CF": "", "AC": "", "SC": "", "AS": "",
        "United": "Utd",
        "Athletic Club": "Athletic Bilbao",
        "Atlético": "Atletico",
        "Internazionale": "Inter",
        "Hellas Verona": "Verona",
        # Argentina
        "Atletico": "Atletico",
        "Independiente Rivadavia": "Ind Rivadavia",
        "Argentinos Juniors": "Argentinos Jrs",
        "Estudiantes de La Plata": "Estudiantes L.P.",
        "Gimnasia La Plata": "Gimnasia LP",
        # Brasil
        "Atletico Mineiro": "Atletico MG",
        "Atletico Paranaense": "Atletico PR",
        "Flamengo": "Flamengo RJ",
        "Chapecoense": "Chapecoense-SC",
    }
    nombre = nombre.strip()
    for k, v in reemplazos.items():
        nombre = nombre.replace(k, v)
    return nombre.strip().lower()

def buscar_rating(nombre_odds_api, ratings_dict):
    nombre_norm = normalizar_nombre(nombre_odds_api)
    # Búsqueda exacta
    for equipo_csv, rating in ratings_dict.items():
        if normalizar_nombre(equipo_csv) == nombre_norm:
            return rating
    # Búsqueda parcial
    for equipo_csv, rating in ratings_dict.items():
        eq_norm = normalizar_nombre(equipo_csv)
        if nombre_norm in eq_norm or eq_norm in nombre_norm:
            return rating
    return None

# ===============================
# ANALIZAR UNA LIGA
# ===============================

def analizar_liga(nombre_liga, sport_key, url_stats, api_key, horas=48):
    logging.info(f"Analizando {nombre_liga}...")

    partidos = obtener_partidos_con_cuotas(sport_key, api_key, horas)
    if not partidos:
        return []

    ratings = calcular_ratings_liga(url_stats)
    if not ratings:
        logging.warning(f"{nombre_liga}: ratings vacíos — se usará x=0 para todos los equipos")

    apuestas = []
    for partido in partidos:
        home    = partido["home_team"]
        away    = partido["away_team"]
        commence = partido.get("commence_time", "")

        try:
            dt_utc  = datetime.strptime(commence, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            dt_arg  = dt_utc - timedelta(hours=3)
            hora_utc = dt_utc.strftime("%d/%m %H:%M UTC")
            hora_arg = dt_arg.strftime("%d/%m %H:%M ARG")
            fecha_partido = dt_arg.strftime("%Y-%m-%d")
        except Exception:
            hora_utc = hora_arg = commence
            fecha_partido = fecha

        cuotas = extraer_cuotas_pinnacle(partido)
        if not cuotas:
            continue
        cuota_h, cuota_d, cuota_a = cuotas

        rating_h   = buscar_rating(home, ratings)
        rating_a   = buscar_rating(away, ratings)
        r_h        = rating_h if rating_h is not None else 0
        r_a        = rating_a if rating_a is not None else 0
        tiene_stats = rating_h is not None and rating_a is not None

        x = r_h - r_a
        p_mod_L, p_mod_E, p_mod_V = motor_probabilidades(x)

        for tipo, p_mod, cuota, label in [
            ("H", p_mod_L, cuota_h, "Local"),
            ("D", p_mod_E, cuota_d, "Empate"),
            ("A", p_mod_V, cuota_a, "Visitante"),
        ]:
            if cuota <= 1.0:
                continue
            p_impl = 100 / cuota
            edge   = p_mod - p_impl
            if edge >= EDGE_MINIMO:
                apuestas.append({
                    "liga":        nombre_liga,
                    "fecha":       fecha_partido,
                    "hora_arg":    hora_arg,
                    "hora_utc":    hora_utc,
                    "local":       home,
                    "visitante":   away,
                    "tipo":        tipo,
                    "apuesta":     label,
                    "cuota":       round(cuota, 2),
                    "prob_modelo": round(p_mod, 1),
                    "prob_impl":   round(p_impl, 1),
                    "edge":        round(edge, 2),
                    "con_stats":   "✅" if tiene_stats else "⚠️ sin historial",
                })

    logging.info(f"{nombre_liga}: {len(apuestas)} value bets detectadas")
    return apuestas

# ===============================
# GUARDAR REPORTE
# ===============================

def guardar_reporte(apuestas, horas):
    if not apuestas:
        return
    df = pd.DataFrame(apuestas)
    df["generado_en"]   = datetime.now().strftime("%Y-%m-%d %H:%M")
    df["ventana_horas"] = horas
    ruta = os.path.join(REPORTS_DIR, "value_bets.csv")
    df.to_csv(ruta, index=False)
    logging.info(f"Reporte guardado: {ruta} | {len(apuestas)} apuestas | ventana {horas}h")

# ===============================
# FUNCION PRINCIPAL
# ===============================

def run(horas=48):
    api_key = get_api_key()
    if not api_key:
        raise ValueError("No se encontró ODDS_API_KEY. Configurala en Streamlit Secrets.")

    todas_apuestas = []
    for nombre, sport_key in LIGAS_ODDS_API.items():
        url_stats = LIGAS_STATS.get(nombre, "")
        apuestas  = analizar_liga(nombre, sport_key, url_stats, api_key, horas)
        todas_apuestas.extend(apuestas)

    guardar_reporte(todas_apuestas, horas)
    logging.info(f"Total value bets detectadas: {len(todas_apuestas)}")
    return todas_apuestas

if __name__ == "__main__":
    resultados = run(horas=48)
    for r in resultados:
        print(r)
