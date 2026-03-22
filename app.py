import pandas as pd
import numpy as np
import requests
from io import StringIO
import os
import logging
import yaml
from datetime import datetime
from bs4 import BeautifulSoup

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
BANKROLL_ARS  = 30000
UNIDADES_BASE = 100
STAKE_UNIDADES = 2
VALOR_UNIDAD  = BANKROLL_ARS / UNIDADES_BASE
EDGE_MINIMO   = 3.0

fecha = datetime.now().strftime("%Y-%m-%d")

logging.basicConfig(
    filename=os.path.join(LOGS_DIR, f"log_{fecha}.txt"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.info("Inicio del sistema Futbol 2026")

# ===============================
# CARGAR LIGAS DESDE YAML
# ===============================

def cargar_ligas():
    try:
        ruta = os.path.join(CONFIG_DIR, "ligas.yaml")
        with open(ruta, "r") as f:
            config = yaml.safe_load(f)
        return config["ligas"]
    except Exception as e:
        logging.error(f"No se pudo cargar ligas.yaml: {e}")
        return {
            "Inglaterra Premier": {"url": "https://www.football-data.co.uk/mmz4281/2526/E0.csv"},
            "Argentina":          {"url": "https://www.football-data.co.uk/new/ARG.csv"}
        }

# ===============================
# FIX CLAVE: NORMALIZAR COLUMNAS
# ARG.csv y BRA.csv usan formato "extra" con nombres distintos:
#   Home/Away/HG/AG/Res  en vez de  HomeTeam/AwayTeam/FTHG/FTAG/FTR
# Esta función unifica ambos formatos antes de procesar.
# ===============================

def normalizar_columnas(df):
    """
    Detecta si el CSV es formato 'extra' (ARG, BRA, MLS, etc.)
    y renombra las columnas al formato estándar que usa el motor.
    """
    renombres = {}

    # Equipo local
    if 'Home' in df.columns and 'HomeTeam' not in df.columns:
        renombres['Home'] = 'HomeTeam'
    # Equipo visitante
    if 'Away' in df.columns and 'AwayTeam' not in df.columns:
        renombres['Away'] = 'AwayTeam'
    # Goles local
    if 'HG' in df.columns and 'FTHG' not in df.columns:
        renombres['HG'] = 'FTHG'
    # Goles visitante
    if 'AG' in df.columns and 'FTAG' not in df.columns:
        renombres['AG'] = 'FTAG'
    # Resultado
    if 'Res' in df.columns and 'FTR' not in df.columns:
        renombres['Res'] = 'FTR'
    # Odds Pinnacle formato extra: PH/PD/PA → PSH/PSD/PSA
    if 'PH' in df.columns and 'PSH' not in df.columns:
        renombres['PH'] = 'PSH'
    if 'PD' in df.columns and 'PSD' not in df.columns:
        renombres['PD'] = 'PSD'
    if 'PA' in df.columns and 'PSA' not in df.columns:
        renombres['PA'] = 'PSA'

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
# CALCULO SUPERIORIDAD
# ===============================

def calcular_superioridad(historial_goles_h, historial_goles_a):
    rating_h = sum(historial_goles_h[-6:])
    rating_a = sum(historial_goles_a[-6:])
    return rating_h - rating_a

# ===============================
# BACKTESTING
# FIX columnas ARG/BRA: normalizar antes de validar
# ===============================

def ejecutar_backtesting(url_csv, nombre_liga):
    logging.info(f"Iniciando analisis liga: {nombre_liga}")

    try:
        response = requests.get(url_csv, timeout=10)
        df = pd.read_csv(StringIO(response.text), encoding='latin1')
    except Exception as e:
        logging.error(f"Error descargando {url_csv}: {e}")
        return {'apuestas': 0, 'p_l': 0}, 0, []

    # ── FIX: normalizar columnas ANTES de validar ──
    df = normalizar_columnas(df)

    columnas_base = ['FTR', 'FTHG', 'FTAG', 'HomeTeam', 'AwayTeam', 'Date']
    faltantes_base = [c for c in columnas_base if c not in df.columns]
    if faltantes_base:
        logging.warning(f"{nombre_liga}: columnas base faltantes {faltantes_base} — se omite")
        logging.warning(f"  Columnas disponibles: {list(df.columns)[:15]}")
        return {'apuestas': 0, 'p_l': 0}, 0, []

    # Detectar columnas de cuotas disponibles
    if all(c in df.columns for c in ['PSH', 'PSD', 'PSA']):
        col_h, col_d, col_a = 'PSH', 'PSD', 'PSA'
    elif all(c in df.columns for c in ['BbAvH', 'BbAvD', 'BbAvA']):
        col_h, col_d, col_a = 'BbAvH', 'BbAvD', 'BbAvA'
    elif all(c in df.columns for c in ['AvgH', 'AvgD', 'AvgA']):
        col_h, col_d, col_a = 'AvgH', 'AvgD', 'AvgA'
    elif all(c in df.columns for c in ['MaxH', 'MaxD', 'MaxA']):
        col_h, col_d, col_a = 'MaxH', 'MaxD', 'MaxA'
    elif all(c in df.columns for c in ['B365H', 'B365D', 'B365A']):
        col_h, col_d, col_a = 'B365H', 'B365D', 'B365A'
    else:
        logging.warning(f"{nombre_liga}: no se encontraron columnas de cuotas — se omite")
        logging.warning(f"  Columnas disponibles: {list(df.columns)[:15]}")
        return {'apuestas': 0, 'p_l': 0}, 0, []

    logging.info(f"{nombre_liga}: usando cuotas {col_h}/{col_d}/{col_a}")

    # ── FIX encoding fechas: formato ARG/BRA puede ser DD/MM/YYYY o YYYY-MM-DD ──
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date'])

    # Separar histórico de futuros
    hoy = pd.Timestamp.now().normalize()
    df_historico = df[df['Date'] < hoy].dropna(subset=['FTR', col_h, col_d, col_a, 'FTHG', 'FTAG'])
    df_futuro    = df[df['Date'] >= hoy]

    logging.info(f"{nombre_liga}: {len(df_historico)} históricos | {len(df_futuro)} futuros")

    # Construir ratings con historial
    equipos_goles = {}
    for _, fila in df_historico.iterrows():
        h = fila['HomeTeam']
        a = fila['AwayTeam']
        if h not in equipos_goles: equipos_goles[h] = []
        if a not in equipos_goles: equipos_goles[a] = []
        try:
            equipos_goles[h].append(float(fila['FTHG']) - float(fila['FTAG']))
            equipos_goles[a].append(float(fila['FTAG']) - float(fila['FTHG']))
        except (ValueError, TypeError):
            continue

    # Backtesting histórico
    stats = {'apuestas': 0, 'p_l': 0}
    apuestas_historicas = []

    for _, fila in df_historico.iterrows():
        h = fila['HomeTeam']
        a = fila['AwayTeam']
        if len(equipos_goles.get(h, [])) >= 6 and len(equipos_goles.get(a, [])) >= 6:
            x = calcular_superioridad(equipos_goles[h], equipos_goles[a])
            p_mod_L, p_mod_E, p_mod_V = motor_probabilidades(x)
            cuotas = [
                ('H', p_mod_L, fila[col_h]),
                ('D', p_mod_E, fila[col_d]),
                ('A', p_mod_V, fila[col_a])
            ]
            for tipo, p_m, cuota in cuotas:
                try:
                    cuota = float(cuota)
                except (ValueError, TypeError):
                    continue
                edge = p_m - (100 / cuota)
                if edge >= EDGE_MINIMO:
                    stats['apuestas'] += 1
                    ganada = (fila['FTR'] == tipo)
                    if ganada:
                        stats['p_l'] += (2 * (cuota - 1))
                    else:
                        stats['p_l'] -= 2
                    apuestas_historicas.append({
                        "liga":        nombre_liga,
                        "fecha":       fila['Date'].strftime("%Y-%m-%d"),
                        "local":       h,
                        "visitante":   a,
                        "tipo":        tipo,
                        "cuota":       round(cuota, 2),
                        "prob_modelo": round(p_m, 2),
                        "edge":        round(edge, 2),
                        "resultado":   "✅" if ganada else "❌"
                    })

    # Value bets en partidos FUTUROS
    apuestas_futuras = []
    for _, fila in df_futuro.iterrows():
        h = fila['HomeTeam']
        a = fila['AwayTeam']
        tiene_cuotas = all(c in fila and pd.notna(fila[c]) for c in [col_h, col_d, col_a])
        if not tiene_cuotas:
            continue
        if len(equipos_goles.get(h, [])) >= 6 and len(equipos_goles.get(a, [])) >= 6:
            x = calcular_superioridad(equipos_goles[h], equipos_goles[a])
            p_mod_L, p_mod_E, p_mod_V = motor_probabilidades(x)
            cuotas = [
                ('H', p_mod_L, fila[col_h]),
                ('D', p_mod_E, fila[col_d]),
                ('A', p_mod_V, fila[col_a])
            ]
            for tipo, p_m, cuota in cuotas:
                try:
                    cuota = float(cuota)
                except (ValueError, TypeError):
                    continue
                if cuota <= 1.0:
                    continue
                edge = p_m - (100 / cuota)
                if edge >= EDGE_MINIMO:
                    apuestas_futuras.append({
                        "liga":        nombre_liga,
                        "fecha":       fila['Date'].strftime("%Y-%m-%d"),
                        "local":       h,
                        "visitante":   a,
                        "tipo":        tipo,
                        "cuota":       round(cuota, 2),
                        "prob_modelo": round(p_m, 2),
                        "edge":        round(edge, 2),
                        "resultado":   "⏳ pendiente"
                    })

    yield_neto = 0
    if stats['apuestas'] > 0:
        yield_neto = (stats['p_l'] / (stats['apuestas'] * 2)) * 100

    todas = apuestas_historicas + apuestas_futuras
    logging.info(f"{nombre_liga} | hist={stats['apuestas']} | yield={yield_neto:.2f}% | futuras={len(apuestas_futuras)}")
    return stats, yield_neto, todas

# ===============================
# GUARDAR REPORTES
# ===============================

def guardar_reportes_historicos(resultados):
    if not resultados:
        return
    df = pd.DataFrame(resultados)
    df["generado_en"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    ruta = os.path.join(REPORTS_DIR, "backtest_historico.csv")
    df.to_csv(ruta, index=False)
    logging.info(f"Reporte histórico guardado: {ruta}")

def guardar_value_bets_futuras(resultados):
    if not resultados:
        return
    df = pd.DataFrame(resultados)
    df["generado_en"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    df["fuente"] = "football-data (cuotas en CSV)"
    ruta = os.path.join(REPORTS_DIR, "value_bets.csv")
    df.to_csv(ruta, index=False)
    logging.info(f"Value bets futuras guardadas: {ruta}")

def guardar_roi(fecha, liga, apuestas, yield_neto):
    archivo = os.path.join(REPORTS_DIR, "roi_historial.csv")
    fila = pd.DataFrame([{
        "fecha":    fecha,
        "liga":     liga,
        "apuestas": apuestas,
        "yield":    round(yield_neto, 2)
    }])
    if os.path.exists(archivo):
        fila.to_csv(archivo, mode="a", header=False, index=False)
    else:
        fila.to_csv(archivo, index=False)

# ===============================
# FUNCION PRINCIPAL
# ===============================

def run():
    ligas = cargar_ligas()
    todas_apuestas = []
    resumen        = []

    for nombre, datos in ligas.items():
        url = datos["url"]
        stats, yield_neto, apuestas = ejecutar_backtesting(url, nombre)
        if stats['apuestas'] > 0:
            guardar_roi(fecha, nombre, stats['apuestas'], yield_neto)
        todas_apuestas.extend(apuestas)
        resumen.append({
            "liga":          nombre,
            "apuestas":      stats['apuestas'],
            "yield %":       round(yield_neto, 2),
            "P&L unidades":  round(stats['p_l'], 2)
        })

    guardar_reportes_historicos(todas_apuestas)
    guardar_value_bets_futuras(todas_apuestas)
    logging.info("Ejecucion finalizada")
    return todas_apuestas, resumen

if __name__ == "__main__":
    run()
