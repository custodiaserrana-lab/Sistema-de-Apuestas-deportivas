"""
bot_telegram.py — Futbol Quant Bot
Corre cada hora. Si hay value bets con edge >= 7% en partidos
de las próximas 3 horas, manda alerta por Telegram.

Variables de entorno requeridas:
  ODDS_API_KEY     — token de The Odds API
  TELEGRAM_TOKEN   — token del bot de Telegram (de BotFather)
  TELEGRAM_CHAT_ID — tu chat_id personal

En Railway/Render: configurarlas en el panel de variables.
Localmente: exportarlas en la terminal antes de correr.
"""

import os
import sys
import time
import logging
import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta, timezone

# ===============================
# CONFIGURACION
# ===============================

EDGE_MINIMO_BOT   = 7.0    # Solo alertas con edge >= 7%
HORAS_ANTICIPACION = 3     # Partidos en las próximas N horas
INTERVALO_CHECKS  = 3600   # Revisar cada 1 hora (en segundos)
TOP_APUESTAS      = 10     # Máximo de apuestas por mensaje

# ===============================
# VARIABLES DE ENTORNO
# ===============================

def get_config():
    odds_key   = os.environ.get("ODDS_API_KEY", "")
    tg_token   = os.environ.get("TELEGRAM_TOKEN", "")
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    errores = []
    if not odds_key:   errores.append("ODDS_API_KEY")
    if not tg_token:   errores.append("TELEGRAM_TOKEN")
    if not tg_chat_id: errores.append("TELEGRAM_CHAT_ID")

    if errores:
        raise ValueError(f"Faltan variables de entorno: {', '.join(errores)}")

    return odds_key, tg_token, tg_chat_id

# ===============================
# LOGGING
# ===============================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# ===============================
# LIGAS
# ===============================

LIGAS_ODDS_API = {
    "Premier League":  "soccer_epl",
    "La Liga":         "soccer_spain_la_liga",
    "Serie A":         "soccer_italy_serie_a",
    "Bundesliga":      "soccer_germany_bundesliga",
    "Ligue 1":         "soccer_france_ligue_one",
    "Eredivisie":      "soccer_netherlands_eredivisie",
    "Portugal":        "soccer_portugal_primeira_liga",
    "Argentina":       "soccer_argentina_primera_division",
    "Brasil":          "soccer_brazil_campeonato",
    "MLS":             "soccer_usa_mls",
}

LIGAS_STATS = {
    "Premier League":  "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "La Liga":         "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "Serie A":         "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    "Bundesliga":      "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
    "Ligue 1":         "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
    "Eredivisie":      "https://www.football-data.co.uk/mmz4281/2526/N1.csv",
    "Portugal":        "https://www.football-data.co.uk/mmz4281/2526/P1.csv",
    "Argentina":       "https://www.football-data.co.uk/new/ARG.csv",
    "Brasil":          "https://www.football-data.co.uk/new/BRA.csv",
    "MLS":             "https://www.football-data.co.uk/new/USA.csv",
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
# RATINGS HISTORICOS
# ===============================

_cache_ratings = {}  # Cache para no descargar el mismo CSV varias veces por sesión

def calcular_ratings_liga(url_csv):
    if url_csv in _cache_ratings:
        return _cache_ratings[url_csv]

    try:
        response = requests.get(url_csv, timeout=10)
        df = pd.read_csv(StringIO(response.text))
    except Exception as e:
        logging.warning(f"Error descargando stats {url_csv}: {e}")
        return {}

    columnas = ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
    if any(c not in df.columns for c in columnas):
        return {}

    df = df.dropna(subset=['FTR', 'FTHG', 'FTAG'])
    historial = {}

    for _, fila in df.iterrows():
        h, a = fila['HomeTeam'], fila['AwayTeam']
        if h not in historial: historial[h] = []
        if a not in historial: historial[a] = []
        historial[h].append(fila['FTHG'] - fila['FTAG'])
        historial[a].append(fila['FTAG'] - fila['FTHG'])

    ratings = {
        eq: sum(hist[-6:])
        for eq, hist in historial.items()
        if len(hist) >= 3
    }

    _cache_ratings[url_csv] = ratings
    return ratings

# ===============================
# NORMALIZAR NOMBRES
# ===============================

def normalizar(nombre):
    reemplazos = {
        "FC": "", "CF": "", "AC": "", "SC": "", "AS": "",
        "United": "Utd", "Athletic Club": "Athletic Bilbao",
        "Internazionale": "Inter", "Hellas Verona": "Verona",
    }
    nombre = nombre.strip()
    for k, v in reemplazos.items():
        nombre = nombre.replace(k, v)
    return nombre.strip().lower()

def buscar_rating(nombre, ratings):
    n = normalizar(nombre)
    for eq, r in ratings.items():
        if normalizar(eq) == n:
            return r
    for eq, r in ratings.items():
        if n in normalizar(eq) or normalizar(eq) in n:
            return r
    return None

# ===============================
# CONSULTAR THE ODDS API
# ===============================

def obtener_partidos(sport_key, api_key, horas):
    ahora = datetime.now(timezone.utc)
    hasta = ahora + timedelta(hours=horas)

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        "apiKey":            api_key,
        "regions":           "eu",
        "markets":           "h2h",
        "oddsFormat":        "decimal",
        "commenceTimeFrom":  ahora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commenceTimeTo":    hasta.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        logging.warning(f"Odds API {sport_key}: status {r.status_code}")
    except Exception as e:
        logging.warning(f"Error consultando {sport_key}: {e}")

    return []

def extraer_cuotas(partido):
    preferidos = ["pinnacle", "betfair_ex_eu", "sport888", "williamhill"]
    mercado = None

    for pref in preferidos:
        for bk in partido.get("bookmakers", []):
            if bk["key"] == pref:
                for m in bk.get("markets", []):
                    if m["key"] == "h2h":
                        mercado = m
                        break
            if mercado: break
        if mercado: break

    if not mercado:
        for bk in partido.get("bookmakers", []):
            for m in bk.get("markets", []):
                if m["key"] == "h2h":
                    mercado = m
                    break
            if mercado: break

    if not mercado:
        return None

    outcomes = {o["name"]: o["price"] for o in mercado.get("outcomes", [])}
    h = outcomes.get(partido["home_team"])
    a = outcomes.get(partido["away_team"])
    d = outcomes.get("Draw")

    return (h, d, a) if h and d and a else None

# ===============================
# DETECTAR VALUE BETS
# ===============================

def detectar_value_bets(odds_key):
    _cache_ratings.clear()  # Limpiar cache al inicio de cada ciclo
    todas = []

    for nombre_liga, sport_key in LIGAS_ODDS_API.items():
        partidos = obtener_partidos(sport_key, odds_key, HORAS_ANTICIPACION)
        if not partidos:
            continue

        url_stats = LIGAS_STATS.get(nombre_liga, "")
        ratings = calcular_ratings_liga(url_stats) if url_stats else {}

        for partido in partidos:
            home = partido["home_team"]
            away = partido["away_team"]

            cuotas = extraer_cuotas(partido)
            if not cuotas:
                continue

            cuota_h, cuota_d, cuota_a = cuotas

            r_h = buscar_rating(home, ratings) or 0
            r_a = buscar_rating(away, ratings) or 0
            tiene_stats = buscar_rating(home, ratings) is not None

            x = r_h - r_a
            p_L, p_E, p_V = motor_probabilidades(x)

            # Hora del partido
            try:
                dt = datetime.strptime(partido["commence_time"], "%Y-%m-%dT%H:%M:%SZ")
                dt = dt.replace(tzinfo=timezone.utc)
                ahora_utc = datetime.now(timezone.utc)
                minutos = int((dt - ahora_utc).total_seconds() / 60)

                # Fecha completa: si es hoy muestra "Hoy", si es mañana muestra "Mañana"
                if dt.date() == ahora_utc.date():
                    dia_str = "Hoy"
                elif dt.date() == (ahora_utc + timedelta(days=1)).date():
                    dia_str = "Mañana"
                else:
                    dia_str = dt.strftime("%d/%m")

                hora_str = f"{dia_str} {dt.strftime('%H:%M')} UTC"
            except Exception:
                minutos = 999
                hora_str = "?"

            for tipo, p_mod, cuota, label in [
                ("H", p_L, cuota_h, "LOCAL"),
                ("D", p_E, cuota_d, "EMPATE"),
                ("A", p_V, cuota_a, "VISITANTE"),
            ]:
                if cuota <= 1.0:
                    continue

                p_impl = 100 / cuota
                edge = p_mod - p_impl

                if edge >= EDGE_MINIMO_BOT:
                    todas.append({
                        "liga":      nombre_liga,
                        "hora":      hora_str,
                        "minutos":   minutos,
                        "local":     home,
                        "visitante": away,
                        "tipo":      tipo,
                        "apuesta":   label,
                        "cuota":     round(cuota, 2),
                        "edge":      round(edge, 2),
                        "stats":     tiene_stats,
                    })

    # Ordenar por edge descendente
    todas.sort(key=lambda x: x["edge"], reverse=True)
    return todas[:TOP_APUESTAS]

# ===============================
# FORMATEAR MENSAJE TELEGRAM
# ===============================

def formatear_mensaje(apuestas):
    ahora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    lineas = [
        f"⚽ *FUTBOL QUANT BOT*",
        f"📅 {ahora}",
        f"🎯 {len(apuestas)} value bet{'s' if len(apuestas) > 1 else ''} detectada{'s' if len(apuestas) > 1 else ''}",
        f"",
    ]

    for i, a in enumerate(apuestas, 1):
        # Emoji según urgencia
        if a["minutos"] <= 60:
            urgencia = "🔴"
        elif a["minutos"] <= 120:
            urgencia = "🟡"
        else:
            urgencia = "🟢"

        # Emoji según tipo
        tipo_emoji = {"H": "🏠", "D": "🤝", "A": "✈️"}.get(a["tipo"], "")

        stats_aviso = "" if a["stats"] else " ⚠️"

        # Texto de tiempo restante
        if minutos < 60:
            tiempo_str = f"{minutos} min"
        elif minutos < 120:
            tiempo_str = f"1h {minutos % 60}min"
        else:
            horas_r = minutos // 60
            tiempo_str = f"{horas_r}h {minutos % 60}min"

        lineas += [
            f"*{i}. {a['liga']}*",
            f"{urgencia} {a['hora']} — faltan {tiempo_str}",
            f"{tipo_emoji} {a['local']} vs {a['visitante']}",
            f"💰 *{a['apuesta']}* | Cuota: `{a['cuota']}` | Edge: `{a['edge']}%`{stats_aviso}",
            f"",
        ]

    lineas += [
        f"─────────────────",
        f"🟢 +3h  🟡 1\\-2h  🔴 \\<1h",
        f"⚠️ = sin historial de goles",
    ]

    return "\n".join(lineas)

# ===============================
# ENVIAR MENSAJE TELEGRAM
# ===============================

def enviar_telegram(mensaje, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id":    chat_id,
        "text":       mensaje,
        "parse_mode": "Markdown",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            logging.info("Mensaje enviado a Telegram ✅")
            return True
        else:
            logging.error(f"Error Telegram: {r.status_code} — {r.text}")
    except Exception as e:
        logging.error(f"Excepción enviando a Telegram: {e}")
    return False

# ===============================
# LOOP PRINCIPAL
# ===============================

def main():
    logging.info("🤖 Futbol Quant Bot iniciado")

    try:
        odds_key, tg_token, tg_chat_id = get_config()
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)

    # Mensaje de inicio
    enviar_telegram(
        f"🤖 *Futbol Quant Bot activo*\n"
        f"Revisando partidos cada hora.\n"
        f"Alertas solo con edge ≥ {EDGE_MINIMO_BOT}% y partidos en próximas {HORAS_ANTICIPACION}h.",
        tg_token, tg_chat_id
    )

    apuestas_enviadas = set()  # Para no repetir la misma apuesta

    while True:
        logging.info("🔍 Buscando value bets...")

        try:
            apuestas = detectar_value_bets(odds_key)

            # Filtrar las que ya se enviaron
            nuevas = []
            for a in apuestas:
                key = f"{a['local']}-{a['visitante']}-{a['tipo']}"
                if key not in apuestas_enviadas:
                    nuevas.append(a)
                    apuestas_enviadas.add(key)

            if nuevas:
                logging.info(f"✅ {len(nuevas)} nuevas value bets — enviando alerta")
                mensaje = formatear_mensaje(nuevas)
                enviar_telegram(mensaje, tg_token, tg_chat_id)
            else:
                logging.info("😴 Sin nuevas value bets en esta revisión")

        except Exception as e:
            logging.error(f"Error en ciclo principal: {e}")

        # Limpiar apuestas viejas cada 12 horas (reset del set)
        if len(apuestas_enviadas) > 200:
            apuestas_enviadas.clear()

        logging.info(f"⏳ Próxima revisión en {INTERVALO_CHECKS // 60} minutos")
        time.sleep(INTERVALO_CHECKS)

if __name__ == "__main__":
    main()
