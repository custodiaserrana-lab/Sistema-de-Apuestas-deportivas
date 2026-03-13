import pandas as pd
import numpy as np
import requests
from io import StringIO

# CONFIGURACIÓN DEL SISTEMA OFICIAL v1.0
BANKROLL_ARS = 30000
UNIDADES_BASE = 100
STAKE_UNIDADES = 2  # 2% del bankroll
VALOR_UNIDAD = BANKROLL_ARS / UNIDADES_BASE
EDGE_MINIMO = 3.0  # Porcentaje mínimo para disparar apuesta

# URLs DE DATOS (Fuentes principales)
URLS = {
    "Argentina": "https://www.football-data.co.uk/new/ARG.csv",
    "Premier_League": "https://www.football-data.co.uk/mmz4281/2526/E0.csv"
}

def descargar_datos(url):
    """Descarga el CSV listo para computadora de Football-Data"""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return pd.read_csv(StringIO(response.text))
    except Exception as e:
        print(f"Error en descarga: {e}")
    return None

def calcular_rating_equipo(df, equipo, fecha_actual):
    """
    Calcula la superioridad de goles en los últimos 6 partidos.
    Rating = Goles Anotados - Goles Recibidos.
    """
    # Filtrar partidos jugados por el equipo antes de la fecha actual
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    pasados = df[df['Date'] < fecha_actual]
    partidos_equipo = pasados[(pasados['HomeTeam'] == equipo) | (pasados['AwayTeam'] == equipo)].tail(6)
    
    if len(partidos_equipo) < 6:
        return None # No hay datos suficientes de "forma reciente"
    
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

def motor_probabilidades(x):
    """Ecuaciones de mejor ajuste de Joseph Buchdahl"""
    prob_L = 1.56 * x + 46.47
    prob_V = 0.03 * (x**2) - 1.27 * x + 23.65
    prob_E = -0.03 * (x**2) - 0.29 * x + 29.48
    return prob_L, prob_E, prob_V

def analizar_jornada(nombre_liga, url):
    df = descargar_datos(url)
    if df is None: return

    print(f"\n--- ANALIZANDO: {nombre_liga} ---")
    
    # Identificar partidos sin resultado (próxima jornada)
    # Nota: Football-Data usa columnas PSH, PSD, PSA para cuotas Pinnacle
    proximos = df[df['FTR'].isna()]
    
    for idx, fila in proximos.iterrows():
        home = fila['HomeTeam']
        away = fila['AwayTeam']
        
        rating_h = calcular_rating_equipo(df, home, fila['Date'])
        rating_a = calcular_rating_equipo(df, away, fila['Date'])
        
        if rating_h is not None and rating_a is not None:
            x = rating_h - rating_a # Calificación del Partido
            p_mod_L, p_mod_E, p_mod_V = motor_probabilidades(x)
            
            # Comparar con cuotas de Pinnacle (Las más sabias)
            cuotas = {'L': fila['PSH'], 'E': fila['PSD'], 'V': fila['PSA']}
            
            for tipo, cuota in cuotas.items():
                if pd.isna(cuota): continue
                
                p_impl = 100 / cuota
                p_mod = p_mod_L if tipo == 'L' else (p_mod_E if tipo == 'E' else p_mod_V)
                edge = p_mod - p_impl
                
                if edge >= EDGE_MINIMO: # Filtro de entrada v1.0
                    print(f"¡VALOR DETECTADO! {home} vs {away} -> {tipo}")
                    print(f"  Rating (x): {x} | Edge: {edge:.2f}% | Cuota: {cuota}")
                    print(f"  STAKE SUGERIDO: {STAKE_UNIDADES}u (${STAKE_UNIDADES * VALOR_UNIDAD:.0f} ARS)")

if __name__ == "__main__":
    for liga, url in URLS.items():
        analizar_jornada(liga, url)
```

