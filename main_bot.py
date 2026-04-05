# main_bot.py - version liviana de main.py para Termux
# Sin pandas, solo requests. Para uso del bot de Telegram.

import os, requests, logging
from datetime import datetime, timedelta, timezone

log = logging.getLogger("FQBot.motor")

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

EDGE_MINIMO = float(os.environ.get("EDGE_MINIMO", "3.0"))


def motor_probabilidades(x):
    p_L = 1.56 * x + 46.47
    p_V = 0.03 * (x**2) - 1.27 * x + 23.65
    p_E = -0.03 * (x**2) - 0.29 * x + 29.48
    return p_L, p_E, p_V


def normalizar_col(headers, *candidatos):
    for c in candidatos:
        if c in headers:
            return c
    return None


def calcular_ratings(url_csv):
    try:
        r = requests.get(url_csv, timeout=12)
        lines = r.content.decode("latin1").splitlines()
        if len(lines) < 2:
            return {}
        headers = [h.strip() for h in lines[0].split(",")]

        col_h   = normalizar_col(headers, "HomeTeam", "Home")
        col_a   = normalizar_col(headers, "AwayTeam", "Away")
        col_fhg = normalizar_col(headers, "FTHG", "HG")
        col_fag = normalizar_col(headers, "FTAG", "AG")
        col_ftr = normalizar_col(headers, "FTR", "Res")

        if not all([col_h, col_a, col_fhg, col_fag, col_ftr]):
            return {}

        ih = headers.index(col_h)
        ia = headers.index(col_a)
        ifhg = headers.index(col_fhg)
        ifag = headers.index(col_fag)
        iftr = headers.index(col_ftr)

        historial = {}
        for line in lines[1:]:
            cols = line.split(",")
            if len(cols) <= max(ih, ia, ifhg, ifag, iftr):
                continue
            h   = cols[ih].strip()
            a   = cols[ia].strip()
            ftr = cols[iftr].strip()
            if not ftr or ftr not in ("H","D","A"):
                continue
            try:
                ghg = float(cols[ifhg])
                gag = float(cols[ifag])
            except ValueError:
                continue
            if h not in historial: historial[h] = []
            if a not in historial: historial[a] = []
            historial[h].append(ghg - gag)
            historial[a].append(gag - ghg)

        ratings = {}
        for eq, hist in historial.items():
            u6 = hist[-6:]
            if len(u6) >= 3:
                ratings[eq] = sum(u6)
        return ratings
    except Exception as e:
        log.warning(f"Error ratings: {e}")
        return {}


def buscar_rating(nombre, ratings):
    n = nombre.strip().lower()
    for eq, r in ratings.items():
        if eq.strip().lower() == n:
            return r
    for eq, r in ratings.items():
        eq_n = eq.strip().lower()
        if n in eq_n or eq_n in n:
            return r
    return None


def analizar_liga(nombre, sport_key, url_stats, api_key, horas=48):
    ahora = datetime.now(timezone.utc)
    hasta = ahora + timedelta(hours=horas)
    url   = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        "apiKey": api_key, "regions": "eu", "markets": "h2h",
        "oddsFormat": "decimal",
        "commenceTimeFrom": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commenceTimeTo":   hasta.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code == 401:
            raise ValueError("HTTP 401 - API key invalida")
        if r.status_code != 200:
            log.warning(f"{nombre}: HTTP {r.status_code}")
            return []
        partidos = r.json()
    except ValueError:
        raise
    except Exception as e:
        log.warning(f"{nombre}: {e}")
        return []

    ratings = calcular_ratings(url_stats) if url_stats else {}
    apuestas = []

    for partido in partidos:
        home    = partido["home_team"]
        away    = partido["away_team"]
        commence = partido.get("commence_time","")
        try:
            dt_utc = datetime.strptime(commence, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            hora_arg = (dt_utc - timedelta(hours=3)).strftime("%d/%m %H:%M")
        except Exception:
            hora_arg = commence

        # extraer cuotas
        bookmakers = partido.get("bookmakers",[])
        mercado = None
        for pref in ["pinnacle","betfair_ex_eu","sport888","williamhill"]:
            for bk in bookmakers:
                if bk["key"] == pref:
                    for m in bk.get("markets",[]):
                        if m["key"] == "h2h":
                            mercado = m; break
                if mercado: break
            if mercado: break
        if not mercado:
            for bk in bookmakers:
                for m in bk.get("markets",[]):
                    if m["key"] == "h2h":
                        mercado = m; break
                if mercado: break
        if not mercado:
            continue

        outcomes = {o["name"]: o["price"] for o in mercado.get("outcomes",[])}
        ch = outcomes.get(home)
        ca = outcomes.get(away)
        cd = outcomes.get("Draw")
        if not all([ch, ca, cd]):
            continue

        rh = buscar_rating(home, ratings)
        ra = buscar_rating(away, ratings)
        x  = (rh or 0) - (ra or 0)
        p_L, p_E, p_V = motor_probabilidades(x)
        tiene_stats = rh is not None and ra is not None

        for tipo, p_m, cuota, label in [
            ("H", p_L, ch, "Local"),
            ("D", p_E, cd, "Empate"),
            ("A", p_V, ca, "Visitante"),
        ]:
            if cuota <= 1.0: continue
            edge = p_m - (100 / cuota)
            if edge >= EDGE_MINIMO:
                apuestas.append({
                    "liga":        nombre,
                    "hora_arg":    hora_arg,
                    "local":       home,
                    "visitante":   away,
                    "tipo":        tipo,
                    "apuesta":     label,
                    "cuota":       round(cuota, 2),
                    "prob_modelo": round(p_m, 1),
                    "prob_impl":   round(100/cuota, 1),
                    "edge":        round(edge, 2),
                    "con_stats":   "si" if tiene_stats else "sin historial",
                })
    return apuestas
