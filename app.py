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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# ===============================
# CONFIGURACION GLOBAL
# ===============================

BANKROLL_ARS = 30000
UNIDADES_BASE = 100
STAKE_UNIDADES = 2
VALOR_UNIDAD = BANKROLL_ARS / UNIDADES_BASE
EDGE_MINIMO = 3.0

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
            "Argentina": {"url": "https://www.football-data.co.uk/new/ARG.csv"}
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
# CALCULO SUPERIORIDAD
# ===============================

def calcular_superioridad(historial_goles_h, historial_goles_a):
    rating_h = sum(historial_goles_h[-6:])
    rating_a = sum(historial_goles_a[-6:])
    return rating_h - rating_a

# ===============================
# BACKTESTING
# FIX: Separa datos históricos (para ratings) de partidos futuros (para detección).
# Solo analiza partidos con Date >= hoy que aún no tienen resultado.
# ===============================

def ejecutar_backtesting(url_csv, nombre_liga):
    logging.info(f"Iniciando analisis liga: {nombre_liga}")

    try:
        response = requests.get(url_csv, timeout=10)
        df = pd.read_csv(StringIO(response.text))
    except Exception as e:
        logging.error(f"Error descargando {url_csv}: {e}")
        return {'apuestas': 0, 'p_l': 0}, 0, []

    columnas_requeridas = ['FTR', 'PSH', 'PSD', 'PSA', 'FTHG', 'FTAG', 'HomeTeam', 'AwayTeam', 'Date']
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        logging.warning(f"{nombre_liga}: columnas faltantes {faltantes} — se omite esta liga")
        return {'apuestas': 0, 'p_l': 0}, 0, []

    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date'])

    # FIX: Separar partidos históricos (con resultado) de futuros (sin resultado)
    hoy = pd.Timestamp.now().normalize()
    df_historico = df[df['Date'] < hoy].dropna(subset=['FTR', 'PSH', 'PSD', 'PSA', 'FTHG', 'FTAG'])
    df_futuro = df[df['Date'] >= hoy]

    logging.info(f"{nombre_liga}: {len(df_historico)} partidos históricos | {len(df_futuro)} partidos futuros/hoy")

    # Construir ratings usando solo el historial
    equipos_goles = {}
    for _, fila in df_historico.iterrows():
        h = fila['HomeTeam']
        a = fila['AwayTeam']
        if h not in equipos_goles:
            equipos_goles[h] = []
        if a not in equipos_goles:
            equipos_goles[a] = []
        equipos_goles[h].append(fila['FTHG'] - fila['FTAG'])
        equipos_goles[a].append(fila['FTAG'] - fila['FTHG'])

    # También ejecutar backtesting clásico sobre histórico para yield/ROI
    stats = {'apuestas': 0, 'p_l': 0}
    apuestas_historicas = []

    for _, fila in df_historico.iterrows():
        h = fila['HomeTeam']
        a = fila['AwayTeam']
        if len(equipos_goles.get(h, [])) >= 6 and len(equipos_goles.get(a, [])) >= 6:
            x = calcular_superioridad(equipos_goles[h], equipos_goles[a])
            p_mod_L, p_mod_E, p_mod_V = motor_probabilidades(x)
            cuotas = [
                ('H', p_mod_L, fila['PSH']),
                ('D', p_mod_E, fila['PSD']),
                ('A', p_mod_V, fila['PSA'])
            ]
            for tipo, p_m, cuota in cuotas:
                edge = p_m - (100 / cuota)
                if edge >= EDGE_MINIMO:
                    stats['apuestas'] += 1
                    ganada = (fila['FTR'] == tipo)
                    if ganada:
                        stats['p_l'] += (2 * (cuota - 1))
                    else:
                        stats['p_l'] -= 2
                    apuestas_historicas.append({
                        "liga": nombre_liga,
                        "fecha": fila['Date'].strftime("%Y-%m-%d"),
                        "local": h,
                        "visitante": a,
                        "tipo": tipo,
                        "cuota": round(cuota, 2),
                        "prob_modelo": round(p_m, 2),
                        "edge": round(edge, 2),
                        "resultado": "✅" if ganada else "❌"
                    })

    # FIX: Detectar value bets en partidos FUTUROS usando ratings ya construidos
    apuestas_futuras = []
    for _, fila in df_futuro.iterrows():
        h = fila['HomeTeam']
        a = fila['AwayTeam']

        # Necesitamos cuotas en el CSV futuro — si no las hay, saltar
        tiene_cuotas = all(c in fila and pd.notna(fila[c]) for c in ['PSH', 'PSD', 'PSA'])
        if not tiene_cuotas:
            continue

        if len(equipos_goles.get(h, [])) >= 6 and len(equipos_goles.get(a, [])) >= 6:
            x = calcular_superioridad(equipos_goles[h], equipos_goles[a])
            p_mod_L, p_mod_E, p_mod_V = motor_probabilidades(x)
            cuotas = [
                ('H', p_mod_L, fila['PSH']),
                ('D', p_mod_E, fila['PSD']),
                ('A', p_mod_V, fila['PSA'])
            ]
            for tipo, p_m, cuota in cuotas:
                if cuota <= 1.0:
                    continue
                edge = p_m - (100 / cuota)
                if edge >= EDGE_MINIMO:
                    apuestas_futuras.append({
                        "liga": nombre_liga,
                        "fecha": fila['Date'].strftime("%Y-%m-%d"),
                        "local": h,
                        "visitante": a,
                        "tipo": tipo,
                        "cuota": round(cuota, 2),
                        "prob_modelo": round(p_m, 2),
                        "edge": round(edge, 2),
                        "resultado": "⏳ pendiente"
                    })

    yield_neto = 0
    if stats['apuestas'] > 0:
        yield_neto = (stats['p_l'] / (stats['apuestas'] * 2)) * 100

    logging.info(f"{nombre_liga} | apuestas_hist={stats['apuestas']} | yield={yield_neto:.2f} | futuras={len(apuestas_futuras)}")
    return stats, yield_neto, apuestas_historicas, apuestas_futuras

# ===============================
# GUARDAR REPORTES
# FIX: CSVs separados para histórico y value bets futuras
# ===============================

def guardar_reportes_historicos(resultados):
    """Guarda el detalle del backtesting histórico — NO sobreescribe value_bets.csv"""
    if not resultados:
        return
    df = pd.DataFrame(resultados)
    df["generado_en"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    ruta = os.path.join(REPORTS_DIR, "backtest_historico.csv")
    df.to_csv(ruta, index=False)
    logging.info(f"Reporte histórico guardado: {ruta}")

def guardar_value_bets_futuras(resultados):
    """Guarda value bets de partidos futuros detectados desde football-data"""
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
        "fecha": fecha,
        "liga": liga,
        "apuestas": apuestas,
        "yield": round(yield_neto, 2)
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
    todas_apuestas_hist = []
    todas_apuestas_futuras = []
    resumen = []

    for nombre, datos in ligas.items():
        url = datos["url"]
        stats, yield_neto, apuestas_hist, apuestas_futuras = ejecutar_backtesting(url, nombre)

        if stats['apuestas'] > 0:
            guardar_roi(fecha, nombre, stats['apuestas'], yield_neto)

        todas_apuestas_hist.extend(apuestas_hist)
        todas_apuestas_futuras.extend(apuestas_futuras)

        resumen.append({
            "liga": nombre,
            "apuestas_hist": stats['apuestas'],
            "value_bets_futuras": len(apuestas_futuras),
            "yield %": round(yield_neto, 2),
            "P&L unidades": round(stats['p_l'], 2)
        })

    # FIX: guardar en CSVs separados
    guardar_reportes_historicos(todas_apuestas_hist)
    guardar_value_bets_futuras(todas_apuestas_futuras)

    logging.info("Ejecucion finalizada")
    # Devolver históricas para mostrar en backtesting, y el resumen
    return todas_apuestas_hist, resumen

if __name__ == "__main__":
    run()
