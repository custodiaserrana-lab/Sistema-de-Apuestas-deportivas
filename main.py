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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

os.makedirs(LOGS_DIR, exist_ok=True)
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

# La API key se lee desde variable de entorno para no exponerla en el código.
# En Streamlit Cloud: Settings → Secrets → agregar ODDS_API_KEY = "tu_token"
# Localmente: crear archivo .env o setear la variable de entorno

import streamlit as st

def get_api_key():
    try:
        return st.secrets["ODDS_API_KEY"]
    except Exception:
        return os.environ.get("ODDS_API_KEY", "")

# ===============================
# LIGAS — mapeo football-data ↔ The Odds API
# ===============================

# The Odds API usa sus propios sport_keys para identificar ligas
LIGAS_ODDS_API = {
    "Premier_League":  "soccer_epl",
    "La_Liga":         "soccer_spain_la_liga",
    "Serie_A":         "soccer_italy_serie_a",
    "Bundesliga":      "soccer_germany_bundesliga",
    "Ligue_1":         "soccer_france_ligue_one",
    "Eredivisie":      "soccer_netherlands_eredivisie",
    "Portugal":        "soccer_portugal_primeira_liga",
    "Argentina":       "soccer_argentina_primera_division",
    "Brasil":          "soccer_brazil_campeonato",
    "MLS":             "soccer_usa_mls",
}

# URLs football-data para estadísticas históricas (ratings)
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
# MOTOR MATEMATICO
# ===============================

def motor_probabilidades(x):
    p_L = 1.56 * x + 46.47
    p_V = 0.03 * (x**2) - 1.27 * x + 23.65
    p_E = -0.03 * (x**2) - 0.29 * x + 29.48
    return p_L, p_E, p_V

# ===============================
# CALCULAR RATING DESDE HISTORICO
# ===============================

def calcular_ratings_liga(url_csv):
    """
    Descarga el CSV histórico y calcula el rating (diferencia goles)
    de cada equipo en sus últimos 6 partidos jugados.
    Devuelve un dict: { nombre_equipo: rating }
    """
    try:
        response = requests.get(url_csv, timeout=10)
        df = pd.read_csv(StringIO(response.text))
    except Exception as e:
        logging.error(f"Error descargando stats: {e}")
        return {}

    columnas_requeridas = ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
    if any(c not in df.columns for c in columnas_requeridas):
        return {}

    # Solo partidos ya jugados
    df = df.dropna(subset=['FTR', 'FTHG', 'FTAG'])

    equipos_historial = {}

    for _, fila in df.iterrows():
        h = fila['HomeTeam']
        a = fila['AwayTeam']

        if h not in equipos_historial:
            equipos_historial[h] = []
        if a not in equipos_historial:
            equipos_historial[a] = []

        equipos_historial[h].append(fila['FTHG'] - fila['FTAG'])
        equipos_historial[a].append(fila['FTAG'] - fila['FTHG'])

    ratings = {}
    for equipo, historial in equipos_historial.items():
        ultimos_6 = historial[-6:]
        if len(ultimos_6) >= 3:  # Mínimo 3 partidos para calcular
            ratings[equipo] = sum(ultimos_6)

    return ratings

# ===============================
# OBTENER PARTIDOS PROXIMOS — The Odds API
# ===============================

def obtener_partidos_con_cuotas(sport_key, api_key, horas=6):
    """
    Consulta The Odds API y devuelve partidos de las próximas N horas
    con cuotas de Pinnacle (bookmaker preferido por el modelo).
    """
    ahora = datetime.now(timezone.utc)
    hasta = ahora + timedelta(hours=horas)

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        "apiKey": api_key,
        "regions": "eu",             # Cuotas europeas (incluye Pinnacle)
        "markets": "h2h",            # Mercado 1X2
        "oddsFormat": "decimal",
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
        logging.info(f"{sport_key}: {len(partidos)} partidos encontrados en próximas {horas}h")
        return partidos

    except Exception as e:
        logging.error(f"Excepción consultando The Odds API ({sport_key}): {e}")
        return []

# ===============================
# EXTRAER CUOTAS PINNACLE
# ===============================

def extraer_cuotas_pinnacle(partido):
    """
    Extrae las cuotas de Pinnacle del objeto partido.
    Si no hay Pinnacle, usa el promedio de los bookmakers disponibles.
    Devuelve (cuota_home, cuota_draw, cuota_away) o None si no hay datos.
    """
    bookmakers = partido.get("bookmakers", [])
    if not bookmakers:
        return None

    # Priorizar Pinnacle
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

    # Si no hay preferido, usar el primero disponible
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

    outcomes = {o["name"]: o["price"] for o in mercado.get("outcomes", [])}

    home_team = partido["home_team"]
    away_team = partido["away_team"]

    cuota_h = outcomes.get(home_team)
    cuota_a = outcomes.get(away_team)
    cuota_d = outcomes.get("Draw")

    if not cuota_h or not cuota_a or not cuota_d:
        return None

    return cuota_h, cuota_d, cuota_a

# ===============================
# NORMALIZAR NOMBRE DE EQUIPO
# ===============================

def normalizar_nombre(nombre):
    """
    Limpia y normaliza nombres de equipos para comparar
    entre The Odds API y football-data.co.uk
    """
    reemplazos = {
        "FC": "", "CF": "", "AC": "", "SC": "", "AS": "",
        "United": "Utd", "Athletic Club": "Athletic Bilbao",
        "Atlético": "Atletico", "Internazionale": "Inter",
        "Hellas Verona": "Verona",
    }
    nombre = nombre.strip()
    for k, v in reemplazos.items():
        nombre = nombre.replace(k, v)
    return nombre.strip().lower()

def buscar_rating(nombre_odds_api, ratings_dict):
    """
    Busca el rating de un equipo haciendo matching flexible de nombres.
    """
    nombre_norm = normalizar_nombre(nombre_odds_api)

    for equipo_csv, rating in ratings_dict.items():
        if normalizar_nombre(equipo_csv) == nombre_norm:
            return rating

    # Matching parcial si no hay exacto
    for equipo_csv, rating in ratings_dict.items():
        if nombre_norm in normalizar_nombre(equipo_csv) or \
           normalizar_nombre(equipo_csv) in nombre_norm:
            return rating

    return None

# ===============================
# ANALIZAR UNA LIGA
# ===============================

def analizar_liga(nombre_liga, sport_key, url_stats, api_key, horas=6):
    """
    Combina cuotas en tiempo real (The Odds API) con ratings históricos
    (football-data) para detectar value bets en los próximos partidos.
    """
    logging.info(f"Analizando {nombre_liga}...")

    # 1. Obtener partidos próximos con cuotas
    partidos = obtener_partidos_con_cuotas(sport_key, api_key, horas)
    if not partidos:
        return []

    # 2. Calcular ratings históricos
    ratings = calcular_ratings_liga(url_stats)
    if not ratings:
        logging.warning(f"{nombre_liga}: no se pudieron calcular ratings históricos")

    apuestas = []

    for partido in partidos:
        home = partido["home_team"]
        away = partido["away_team"]
        commence = partido.get("commence_time", "")

        # Convertir hora UTC a legible
        try:
            dt = datetime.strptime(commence, "%Y-%m-%dT%H:%M:%SZ")
            dt = dt.replace(tzinfo=timezone.utc)
            hora_local = dt.strftime("%d/%m %H:%M UTC")
        except Exception:
            hora_local = commence

        # Extraer cuotas
        cuotas = extraer_cuotas_pinnacle(partido)
        if not cuotas:
            continue

        cuota_h, cuota_d, cuota_a = cuotas

        # Buscar ratings
        rating_h = buscar_rating(home, ratings)
        rating_a = buscar_rating(away, ratings)

        # Si no hay ratings, usar 0 (modelo sin ventaja histórica)
        r_h = rating_h if rating_h is not None else 0
        r_a = rating_a if rating_a is not None else 0
        tiene_stats = rating_h is not None and rating_a is not None

        x = r_h - r_a
        p_mod_L, p_mod_E, p_mod_V = motor_probabilidades(x)

        mercados = [
            ("H", p_mod_L, cuota_h, "Local"),
            ("D", p_mod_E, cuota_d, "Empate"),
            ("A", p_mod_V, cuota_a, "Visitante"),
        ]

        for tipo, p_mod, cuota, label in mercados:
            if cuota <= 1.0:
                continue

            p_impl = 100 / cuota
            edge = p_mod - p_impl

            if edge >= EDGE_MINIMO:
                apuestas.append({
                    "liga":        nombre_liga,
                    "hora":        hora_local,
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

def guardar_reporte(apuestas):
    if not apuestas:
        return
    df = pd.DataFrame(apuestas)
    ruta = os.path.join(REPORTS_DIR, "value_bets.csv")
    df.to_csv(ruta, index=False)
    logging.info(f"Reporte guardado: {ruta}")

# ===============================
# FUNCION PRINCIPAL
# ===============================

def run(horas=6):
    api_key = get_api_key()
    if not api_key:
        raise ValueError("No se encontró ODDS_API_KEY. Configurala en Streamlit Secrets.")

    todas_apuestas = []

    for nombre, sport_key in LIGAS_ODDS_API.items():
        url_stats = LIGAS_STATS.get(nombre, "")
        apuestas = analizar_liga(nombre, sport_key, url_stats, api_key, horas)
        todas_apuestas.extend(apuestas)

    guardar_reporte(todas_apuestas)
    logging.info(f"Total value bets detectadas: {len(todas_apuestas)}")
    return todas_apuestas

if __name__ == "__main__":
    resultados = run(horas=6)
    for r in resultados:
        print(r)
