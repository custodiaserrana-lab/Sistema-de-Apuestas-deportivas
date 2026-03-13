import pandas as pd
import numpy as np
import requests
from io import StringIO
import os
import logging
from datetime import datetime

# ============================
# CONFIGURACION DEL SISTEMA
# ============================

BANKROLL_ARS = 30000
UNIDADES_BASE = 100
STAKE_UNIDADES = 2
VALOR_UNIDAD = BANKROLL_ARS / UNIDADES_BASE
EDGE_MINIMO = 3.0

# ============================
# CREAR CARPETAS
# ============================

os.makedirs("logs", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# ============================
# CONFIGURAR LOGS
# ============================

fecha = datetime.now().strftime("%Y-%m-%d")

logging.basicConfig(
    filename=f"logs/log_{fecha}.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Inicio sistema Futbol 2026")

# ============================
# LIGAS A ANALIZAR
# ============================

URLS = {
    "Argentina": "https://www.football-data.co.uk/new/ARG.csv",
    "Premier_League": "https://www.football-data.co.uk/mmz4281/2526/E0.csv"
}

# ============================
# DESCARGA DATOS
# ============================

def descargar_datos(url):

    try:

        response = requests.get(url)

        if response.status_code == 200:

            df = pd.read_csv(StringIO(response.text))

            return df

    except Exception as e:

        logging.error(f"Error descarga {url}: {e}")

    return None

# ============================
# CALCULO RATING
# ============================

def calcular_rating_equipo(df, equipo, fecha_actual):

    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

    pasados = df[df['Date'] < fecha_actual]

    partidos_equipo = pasados[
        (pasados['HomeTeam'] == equipo) |
        (pasados['AwayTeam'] == equipo)
    ].tail(6)

    if len(partidos_equipo) < 6:
        return None

    goles_fave = 0
    goles_contra = 0

    for _, fila in partidos_equipo.iterrows():

        if fila['HomeTeam'] == equipo:

            goles_fave += fila['FTHG']
            goles_contra += fila['FTAG']

        else:

            goles_fave += fila['FTAG']
            goles_contra += fila['FTHG']

    return goles_fave - goles_contra

# ============================
# MOTOR PROBABILIDADES
# ============================

def motor_probabilidades(x):

    prob_L = 1.56 * x + 46.47
    prob_V = 0.03 * (x**2) - 1.27 * x + 23.65
    prob_E = -0.03 * (x**2) - 0.29 * x + 29.48

    return prob_L, prob_E, prob_V

# ============================
# ANALISIS PARTIDOS
# ============================

def analizar_jornada(nombre_liga, url):

    df = descargar_datos(url)

    if df is None:

        logging.warning(f"No se pudo analizar {nombre_liga}")

        return []

    logging.info(f"Analizando liga {nombre_liga}")

    proximos = df[df['FTR'].isna()]

    apuestas_detectadas = []

    for idx, fila in proximos.iterrows():

        home = fila['HomeTeam']
        away = fila['AwayTeam']

        rating_h = calcular_rating_equipo(df, home, fila['Date'])
        rating_a = calcular_rating_equipo(df, away, fila['Date'])

        if rating_h is None or rating_a is None:
            continue

        x = rating_h - rating_a

        p_mod_L, p_mod_E, p_mod_V = motor_probabilidades(x)

        cuotas = {
            'L': fila['PSH'],
            'E': fila['PSD'],
            'V': fila['PSA']
        }

        for tipo, cuota in cuotas.items():

            if pd.isna(cuota):
                continue

            p_impl = 100 / cuota

            if tipo == 'L':
                p_mod = p_mod_L
            elif tipo == 'E':
                p_mod = p_mod_E
            else:
                p_mod = p_mod_V

            edge = p_mod - p_impl

            if edge >= EDGE_MINIMO:

                logging.info(f"VALUE BET {home} vs {away} {tipo} edge {edge}")

                apuestas_detectadas.append({
                    "liga": nombre_liga,
                    "local": home,
                    "visitante": away,
                    "tipo": tipo,
                    "cuota": cuota,
                    "edge": edge,
                    "rating": x
                })

    return apuestas_detectadas

# ============================
# GUARDAR REPORTES
# ============================

def guardar_reportes(apuestas):

    if len(apuestas) == 0:

        logging.info("No se detectaron apuestas")

        return

    df = pd.DataFrame(apuestas)

    archivo
