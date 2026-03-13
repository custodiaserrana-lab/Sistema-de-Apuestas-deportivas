import pandas as pd
import numpy as np
import requests
from io import StringIO
import os
import logging
from datetime import datetime

# ===============================
# 1. CONFIGURACION GLOBAL
# ===============================

BANKROLL_ARS = 30000
UNIDADES_BASE = 100
STAKE_UNIDADES = 2
VALOR_UNIDAD = BANKROLL_ARS / UNIDADES_BASE
EDGE_MINIMO = 3.0

# ===============================
# 2. CREACION DE CARPETAS
# ===============================

os.makedirs("logs", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# ===============================
# 3. CONFIGURACION LOGS
# ===============================

fecha = datetime.now().strftime("%Y-%m-%d")

logging.basicConfig(
    filename=f"logs/log_{fecha}.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Inicio del sistema Futbol 2026")

# ===============================
# 4. MOTOR MATEMATICO
# ===============================

def motor_probabilidades(x):
    p_L = 1.56 * x + 46.47
    p_V = 0.03 * (x**2) - 1.27 * x + 23.65
    p_E = -0.03 * (x**2) - 0.29 * x + 29.48
    return p_L, p_E, p_V

# ===============================
# 5. CALCULO SUPERIORIDAD
# ===============================

def calcular_superioridad(historial_goles_h, historial_goles_a):

    rating_h = sum(historial_goles_h[-6:])
    rating_a = sum(historial_goles_a[-6:])

    return rating_h - rating_a

# ===============================
# 6. BACKTESTING
# ===============================

def ejecutar_backtesting(url_csv, nombre_liga):

    logging.info(f"Iniciando analisis liga: {nombre_liga}")

    df = pd.read_csv(url_csv)

    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

    df = df.dropna(subset=['FTR','PSH','PSD','PSA','FTHG','FTAG'])

    equipos_goles = {}

    stats = {
        'apuestas':0,
        'p_l':0
    }

    apuestas_detectadas = []

    for _, fila in df.iterrows():

        h = fila['HomeTeam']
        a = fila['AwayTeam']

        if h not in equipos_goles:
            equipos_goles[h] = []

        if a not in equipos_goles:
            equipos_goles[a] = []

        if len(equipos_goles[h]) >= 6 and len(equipos_goles[a]) >= 6:

            x = calcular_superioridad(equipos_goles[h], equipos_goles[a])

            p_mod_L, p_mod_E, p_mod_V = motor_probabilidades(x)

            cuotas = [
                ('H',p_mod_L,fila['PSH']),
                ('D',p_mod_E,fila['PSD']),
                ('A',p_mod_V,fila['PSA'])
            ]

            for tipo,p_m,cuota in cuotas:

                edge = p_m - (100/cuota)

                if edge >= EDGE_MINIMO:

                    stats['apuestas'] += 1

                    ganada = (fila['FTR'] == tipo)

                    if ganada:
                        stats['p_l'] += (2*(cuota-1))
                    else:
                        stats['p_l'] -= 2

                    apuestas_detectadas.append({
                        "liga":nombre_liga,
                        "local":h,
                        "visitante":a,
                        "tipo":tipo,
                        "cuota":cuota,
                        "prob_modelo":p_m,
                        "edge":edge
                    })

        equipos_goles[h].append(fila['FTHG'] - fila['FTAG'])
        equipos_goles[a].append(fila['FTAG'] - fila['FTHG'])

    yield_neto = 0

    if stats['apuestas'] > 0:
        yield_neto = (stats['p_l']/(stats['apuestas']*2))*100

    logging.info(f"{nombre_liga} | apuestas={stats['apuestas']} | yield={yield_neto:.2f}")

    return stats, yield_neto, apuestas_detectadas

# ===============================
# 7. GUARDAR REPORTES
# ===============================

def guardar_reportes(resultados):

    df = pd.DataFrame(resultados)

    ruta = f"reports/value_bets_{fecha}.csv"

    df.to_csv(ruta,index=False)

    logging.info(f"Reporte guardado: {ruta}")

# ===============================
# 8. HISTORIAL ROI
# ===============================

def guardar_roi(fecha,liga,apuestas,yield_neto):

    archivo = "reports/roi_historial.csv"

    fila = pd.DataFrame([{
        "fecha":fecha,
        "liga":liga,
        "apuestas":apuestas,
        "yield":yield_neto
    }])

    if os.path.exists(archivo):
        fila.to_csv(archivo,mode="a",header=False,index=False)
    else:
        fila.to_csv(archivo,index=False)

# ===============================
# 9. BLOQUE PRINCIPAL
# ===============================

if __name__ == "__main__":

    ligas = {
        "Inglaterra_Premier":"https://www.football-data.co.uk/mmz4281/2425/E0.csv",
        "Argentina_Primera":"https://www.football-data.co.uk/new/ARG.csv"
    }

    todas_apuestas = []

    for nombre,url in ligas.items():

        stats,yield_neto,apuestas = ejecutar_backtesting(url,nombre)

        guardar_roi(fecha,nombre,stats['apuestas'],yield_neto)

        todas_apuestas.extend(apuestas)

    guardar_reportes(todas_apuestas)

    logging.info("Ejecucion finalizada")
