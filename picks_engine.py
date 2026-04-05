   """
picks_engine.py — Motor de selección de picks del día
Futbol Quant Bot — Custodia Serrana Lab © 2026

Este módulo es el PUENTE entre tu sistema existente de value bets
(Sistema-de-Apuestas-deportivas en GitHub) y el bot de Telegram.

ARQUITECTURA:
    Tu sistema actual → picks_engine.py → bot.py → Canal Telegram

CÓMO CONECTAR TU SISTEMA EXISTENTE:
    1. Si usás Streamlit Cloud con Google Sheets → leer de Sheets via gspread
    2. Si guardás CSV → leer el CSV de bets del día
    3. Si tenés API propia → hacer fetch a tu endpoint
"""

import logging
from datetime import datetime
from typing import Optional
import pytz

logger = logging.getLogger(__name__)
ARG_TZ = pytz.timezone("America/Argentina/Buenos_Aires")


# ─────────────────────────────────────────────
# Estructura de un Pick
# ─────────────────────────────────────────────
def make_pick(
    partido: str,
    liga: str,
    hora: str,
    mercado: str,
    cuota: float,
    prob_real: float,
    stake_pct: Optional[float] = None,
) -> dict:
    """
    Crea un pick estandarizado con cálculo automático de EV y Kelly.
    
    Args:
        partido: "Arsenal vs Chelsea"
        liga: "Premier League"
        hora: "20:45" (horario ARG)
        mercado: "1X2 — Local" | "Over 2.5" | "BTTS" etc.
        cuota: cuota decimal (ej: 1.85)
        prob_real: probabilidad real estimada (0.0 a 1.0)
        stake_pct: % del bankroll (si None, se calcula con Kelly)
    """
    prob_implicita = 1 / cuota
    ev = ((prob_real * cuota) - 1) * 100  # EV en %

    # Kelly Criterion: f* = (bp - q) / b
    # b = cuota - 1, p = prob_real, q = 1 - prob_real
    b = cuota - 1
    p = prob_real
    q = 1 - p
    kelly_full = (b * p - q) / b
    kelly_fraccionado = round(kelly_full * 0.25 * 100, 1)  # Kelly al 25%

    return {
        "partido": partido,
        "liga": liga,
        "hora": hora,
        "mercado": mercado,
        "cuota": cuota,
        "prob_real": round(prob_real * 100, 1),
        "prob_implicita": round(prob_implicita * 100, 1),
        "ev": round(ev, 1),
        "stake_kelly": stake_pct if stake_pct else max(1.0, min(kelly_fraccionado, 5.0)),
    }


# ─────────────────────────────────────────────
# Filtros de calidad
# ─────────────────────────────────────────────
EV_MINIMO = 5.0       # % mínimo de Expected Value
CUOTA_MIN = 1.50      # cuota mínima
CUOTA_MAX = 4.00      # cuota máxima (evitar longshots)


def es_pick_valido(pick: dict) -> bool:
    """Aplica filtros de calidad antes de publicar."""
    return (
        pick["ev"] >= EV_MINIMO
        and CUOTA_MIN <= pick["cuota"] <= CUOTA_MAX
    )


# ─────────────────────────────────────────────
# Fuente de datos — CONECTAR CON TU SISTEMA
# ─────────────────────────────────────────────

def get_picks_from_google_sheets() -> list[dict]:
    """
    OPCIÓN A: Leer picks desde Google Sheets SIN credenciales.

    Requisito: la hoja debe estar compartida como
    "Cualquiera con el link puede VER" (solo lectura pública).

    Columnas esperadas en la hoja:
        Fecha | Partido | Liga | Hora | Mercado | Cuota | Prob_Real | Estado

    Estado debe ser "PENDIENTE" para que el pick sea incluido.
    Fecha debe estar en formato dd/mm/YYYY (ej: 05/04/2026).
    """
    import csv
    import io
    import requests

    sheet_id = os.environ.get("SHEET_ID", "")
    if not sheet_id:
        logger.warning("SHEET_ID no configurado en .env")
        return []

    # Exportar hoja como CSV público — sin autenticación
    url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&gid=0"
    )

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        hoy = datetime.now(ARG_TZ).strftime("%d/%m/%Y")
        reader = csv.DictReader(io.StringIO(r.text))

        picks_hoy = []
        for row in reader:
            if row.get("Fecha") == hoy and row.get("Estado") == "PENDIENTE":
                try:
                    pick = make_pick(
                        partido=row["Partido"],
                        liga=row["Liga"],
                        hora=row["Hora"],
                        mercado=row["Mercado"],
                        cuota=float(row["Cuota"]),
                        prob_real=float(row["Prob_Real"]),
                    )
                    if es_pick_valido(pick):
                        picks_hoy.append(pick)
                except (KeyError, ValueError) as e:
                    logger.error(f"Fila con datos incorrectos: {row} — {e}")
                    continue

        logger.info(f"📋 {len(picks_hoy)} picks válidos encontrados en Sheets")
        return picks_hoy

    except requests.exceptions.HTTPError as e:
        logger.error(f"Error HTTP al leer Sheet: {e} — ¿La hoja es pública?")
        return []
    except Exception as e:
        logger.error(f"Error leyendo Google Sheets: {e}")
        return []


def get_picks_hardcoded() -> list[dict]:
    """
    OPCIÓN B: Picks definidos manualmente (para testing o días sin sistema).
    Reemplazar con picks reales cuando corresponda.
    """
    picks_raw = [
        make_pick(
            partido="Manchester City vs Arsenal",
            liga="Premier League",
            hora="21:00",
            mercado="Over 2.5 goles",
            cuota=1.72,
            prob_real=0.68,
        ),
        make_pick(
            partido="Real Madrid vs Barcelona",
            liga="La Liga",
            hora="16:00",
            mercado="BTTS (Ambos anotan)",
            cuota=1.85,
            prob_real=0.63,
        ),
        make_pick(
            partido="River Plate vs Boca Juniors",
            liga="Liga Profesional Argentina",
            hora="17:00",
            mercado="1X2 — Empate",
            cuota=3.20,
            prob_real=0.38,
        ),
    ]
    return [p for p in picks_raw if es_pick_valido(p)]


# ─────────────────────────────────────────────
# Función principal — llamada desde bot.py
# ─────────────────────────────────────────────
def get_picks_of_day() -> list[dict]:
    """
    Punto de entrada principal.
    Intenta Google Sheets primero, fallback a hardcoded.
    """
    # Intentar fuente primaria (tu sistema)
    picks = get_picks_from_google_sheets()

    if picks:
        logger.info(f"✅ {len(picks)} picks obtenidos de Google Sheets")
        return picks

    # Fallback
    logger.warning("⚠️ Sin datos de Sheets — usando picks de ejemplo")
    picks = get_picks_hardcoded()
    logger.info(f"📋 {len(picks)} picks de ejemplo disponibles")
    return picks
                        
