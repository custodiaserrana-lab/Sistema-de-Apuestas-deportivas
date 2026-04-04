# =============================================================
# telegram_bot/messages.py
# Templates de mensajes para el bot de Telegram
# Custodia Serrana Lab 2026
# =============================================================

from datetime import datetime, timezone, timedelta


def ts_arg():
    """Timestamp actual en hora Argentina (GMT-3)."""
    return (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")


# -- Banderas por liga --
LIGA_FLAGS = {
    "Premier_League": "ENG",
    "La_Liga":        "ESP",
    "Serie_A":        "ITA",
    "Bundesliga":     "GER",
    "Ligue_1":        "FRA",
    "Eredivisie":     "NED",
    "Portugal":       "POR",
    "Argentina":      "ARG",
    "Brasil":         "BRA",
    "MLS":            "USA",
}

TIPO_LABELS = {
    "H": "LOCAL",
    "D": "EMPATE",
    "A": "VISITANTE",
}

TIPO_EMOJI = {
    "H": "🏠",
    "D": "🤝",
    "A": "✈️",
}


def msg_bienvenida():
    return (
        "⚽ *FUTBOL QUANT BOT*\n"
        "_Custodia Serrana Lab — Sistema Cuantitativo de Value Betting_\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Comandos disponibles:\n"
        "\n"
        "/scan — Escanear value bets (48h)\n"
        "/scan\\_12 — Partidos próximas 12h\n"
        "/scan\\_24 — Partidos próximas 24h\n"
        "/scan\\_72 — Partidos próximas 72h\n"
        "/ligas — Ver ligas activas\n"
        "/ranking — Top bets por edge\n"
        "/estado — Estado del sistema\n"
        "/ayuda — Mostrar este menú\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Generado: {ts_arg()} ARG_"
    )


def msg_escaneando(horas: int, ligas: int):
    return (
        f"🔍 *Escaneando mercados...*\n"
        f"Ventana: {horas}h | Ligas: {ligas}\n"
        f"_Esto puede tardar 15-30 segundos..._"
    )


def msg_sin_resultados(horas: int):
    return (
        f"⊘ *Sin value bets en las próximas {horas}h*\n\n"
        "Posibles causas:\n"
        "• Edge mínimo muy alto (default 3%)\n"
        "• Pocos partidos en la ventana\n"
        "• Cuotas sin movimiento de valor\n\n"
        "_Probá /scan\\_72 para ampliar la ventana_"
    )


def msg_error_api():
    return (
        "❌ *Error de conexión con The Odds API*\n\n"
        "Verificar:\n"
        "• Variable `ODDS_API_KEY` en Railway\n"
        "• Quota de requests disponible\n"
        "• Estado: https://the-odds-api.com\n\n"
        "_HTTP 401 = API key inválida o no configurada_"
    )


def msg_value_bet(ap: dict, rank: int = None) -> str:
    """Formatea una apuesta individual para Telegram (Markdown)."""
    liga_raw = ap.get("liga", ap.get("Liga", ""))
    flag     = LIGA_FLAGS.get(liga_raw, liga_raw[:3].upper())
    tipo     = ap.get("tipo", ap.get("Tipo", "?"))
    emoji    = TIPO_EMOJI.get(tipo, "⚡")
    label    = TIPO_LABELS.get(tipo, tipo)

    local     = ap.get("local",     ap.get("Local",     "?"))
    visitante = ap.get("visitante", ap.get("Visitante", "?"))
    cuota     = ap.get("cuota",     ap.get("Cuota",     0))
    edge      = ap.get("edge",      ap.get("Edge %",    0))
    prob_mod  = ap.get("prob_modelo", ap.get("% Modelo", 0))
    prob_impl = ap.get("prob_impl",   ap.get("% Impl",   0))
    hora_arg  = ap.get("hora_arg",  ap.get("Fecha ARG", ""))
    stats_ok  = ap.get("con_stats", ap.get("Stats", "?"))
    kelly_u   = ap.get("Stake U",   "—")
    stake_ars = ap.get("Stake ARS", "—")

    rank_str = f"#{rank} " if rank else ""

    lines = [
        f"{'⚡' if edge >= 10 else '🔵' if edge >= 6 else '🟢'} *{rank_str}{local} vs {visitante}*",
        f"`[{flag}]` {hora_arg} ARG",
        f"",
        f"{emoji} *Apostar: {label}*",
        f"Cuota: `{cuota}` | Edge: `+{edge}%`",
        f"P.Modelo: `{prob_mod}%` → P.Impl: `{prob_impl}%`",
    ]

    if kelly_u and kelly_u != "—":
        lines.append(f"Kelly: `{kelly_u}u` | Stake: `${int(stake_ars):,} ARS`")

    lines.append(f"Stats: {stats_ok}")

    return "\n".join(lines)


def msg_resumen_scan(apuestas: list, horas: int) -> str:
    """Mensaje resumen al inicio del scan."""
    total    = len(apuestas)
    ligas_u  = len(set(a.get("liga", a.get("Liga", "")) for a in apuestas))
    edge_max = max((a.get("edge", a.get("Edge %", 0)) for a in apuestas), default=0)
    edge_avg = sum(a.get("edge", a.get("Edge %", 0)) for a in apuestas) / total if total else 0

    return (
        f"✅ *{total} VALUE BETS detectadas*\n"
        f"Ventana: {horas}h | Ligas: {ligas_u}\n"
        f"Edge max: `+{edge_max:.1f}%` | Prom: `+{edge_avg:.1f}%`\n"
        f"`{ts_arg()} ARG`\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )


def msg_estado(api_ok: bool, ligas_activas: int, version: str = "2.0") -> str:
    api_str = "✅ Conectada" if api_ok else "❌ Sin conexión"
    return (
        f"📊 *ESTADO DEL SISTEMA*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Version: `v{version}`\n"
        f"The Odds API: {api_str}\n"
        f"Ligas activas: `{ligas_activas}`\n"
        f"Motor: Custodia Serrana Lab\n"
        f"Timestamp: `{ts_arg()} ARG`\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )


def msg_ligas(ligas: dict) -> str:
    lines = ["📋 *LIGAS ACTIVAS*", "━━━━━━━━━━━━━━━━━━━━━"]
    for nombre, sport_key in ligas.items():
        flag = LIGA_FLAGS.get(nombre, "⚽")
        lines.append(f"`{flag}` {nombre.replace('_', ' ')}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"_Total: {len(ligas)} ligas_")
    return "\n".join(lines)
    
