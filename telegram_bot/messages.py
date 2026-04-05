from datetime import datetime, timezone, timedelta

LIGA_FLAGS = {
    "Premier_League":"ENG","La_Liga":"ESP","Serie_A":"ITA",
    "Bundesliga":"GER","Ligue_1":"FRA","Eredivisie":"NED",
    "Portugal":"POR","Argentina":"ARG","Brasil":"BRA","MLS":"USA",
}
TIPO_LABELS = {"H":"LOCAL","D":"EMPATE","A":"VISITANTE"}
TIPO_EMOJI  = {"H":"🏠","D":"🤝","A":"✈️"}

def ts_arg():
    return (datetime.now(timezone.utc)-timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")

def msg_bienvenida():
    return (
        "⚽ *FUTBOL QUANT BOT*\n"
        "_Custodia Serrana Lab 2026_\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "/scan — Value bets 48h\n"
        "/scan\\_12 — Proximas 12h\n"
        "/scan\\_24 — Proximas 24h\n"
        "/scan\\_72 — Proximas 72h\n"
        "/ranking — Top 10 por edge\n"
        "/ligas — Ligas activas\n"
        "/estado — Estado del sistema\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )

def msg_escaneando(horas, ligas):
    return f"🔍 *Escaneando {ligas} ligas — ventana {horas}h...*\n_Espera 20-30 segundos_"

def msg_sin_resultados(horas):
    return f"⊘ *Sin value bets en {horas}h*\n_Proba /scan\\_72 para ampliar la ventana_"

def msg_error_api():
    return (
        "❌ *Error HTTP 401 — API key invalida*\n\n"
        "Verificar en el archivo .env:\n"
        "`ODDS_API_KEY=tu_key_real`\n\n"
        "_Obtener key en: the-odds-api.com_"
    )

def msg_value_bet(ap, rank=None):
    liga  = ap.get("liga","")
    flag  = LIGA_FLAGS.get(liga, liga[:3].upper())
    tipo  = ap.get("tipo","?")
    emoji = TIPO_EMOJI.get(tipo,"⚡")
    label = TIPO_LABELS.get(tipo, tipo)
    edge  = ap.get("edge",0)
    icono = "⚡" if edge>=10 else "🔵" if edge>=6 else "🟢"
    rank_str = f"#{rank} " if rank else ""
    lines = [
        f"{icono} *{rank_str}{ap.get('local','?')} vs {ap.get('visitante','?')}*",
        f"`[{flag}]` {ap.get('hora_arg','')}",
        f"",
        f"{emoji} *Apostar: {label}*",
        f"Cuota: `{ap.get('cuota',0)}` | Edge: `+{edge}%`",
        f"P.Modelo: `{ap.get('prob_modelo',0)}%` → Impl: `{ap.get('prob_impl',0)}%`",
        f"Stats: {ap.get('con_stats','?')}",
    ]
    return "\n".join(lines)

def msg_resumen_scan(apuestas, horas):
    total   = len(apuestas)
    ligas_u = len(set(a.get("liga","") for a in apuestas))
    edge_max = max((a.get("edge",0) for a in apuestas), default=0)
    edge_avg = sum(a.get("edge",0) for a in apuestas)/total if total else 0
    return (
        f"✅ *{total} VALUE BETS detectadas*\n"
        f"Ventana: {horas}h | Ligas: {ligas_u}\n"
        f"Edge max: `+{edge_max:.1f}%` | Prom: `+{edge_avg:.1f}%`\n"
        f"`{ts_arg()} ARG`\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )

def msg_estado(api_ok, ligas):
    return (
        f"📊 *ESTADO DEL SISTEMA*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"The Odds API: {'✅ OK' if api_ok else '❌ Sin conexion'}\n"
        f"Ligas activas: `{ligas}`\n"
        f"Timestamp: `{ts_arg()} ARG`\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )

def msg_ligas(ligas):
    lines = ["📋 *LIGAS ACTIVAS*","━━━━━━━━━━━━━━━━━━━━━"]
    for n in ligas:
        lines.append(f"`{LIGA_FLAGS.get(n,'⚽')}` {n.replace('_',' ')}")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━\n_Total: {len(ligas)} ligas_")
    return "\n".join(lines)
