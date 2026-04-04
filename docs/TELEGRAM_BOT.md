# Futbol Quant Bot — Documentacion Telegram

**Custodia Serrana Lab 2026**

---

## Arquitectura

```
Sistema-de-Apuestas-deportivas/
├── main.py                   # Motor cuantitativo (The Odds API + ratings)
├── app.py                    # Motor backtesting (football-data.co.uk)
├── streamlit_app.py          # Dashboard web (Streamlit Cloud)
├── telegram_bot/
│   ├── __init__.py
│   ├── bot.py                # Bot principal (aiogram v3)
│   └── messages.py           # Templates de mensajes
├── config/
│   └── ligas.yaml            # Config de ligas
├── requirements.txt          # Dependencias
├── Procfile                  # Comando Railway
└── .env.example              # Variables de entorno
```

---

## Comandos del Bot

| Comando | Descripcion |
|---------|-------------|
| `/start` | Bienvenida y menu |
| `/scan` | Value bets proximas 48h |
| `/scan_12` | Value bets proximas 12h |
| `/scan_24` | Value bets proximas 24h |
| `/scan_72` | Value bets proximas 72h |
| `/ranking` | Top 10 bets por edge |
| `/ligas` | Ligas activas |
| `/estado` | Estado del sistema |
| `/ayuda` | Mostrar menu |

---

## Deploy en Railway

### 1. Variables de entorno en Railway

En tu proyecto Railway → Variables:

```
TELEGRAM_BOT_TOKEN = 123456789:ABCdef...
ODDS_API_KEY       = tu_key_de_the_odds_api
EDGE_MINIMO        = 3.0
HORAS_DEFAULT      = 48
MAX_BETS_MSG       = 15
MELBET_LINK        = https://refmelbet.com/L?tag=d_XXXXXX
```

### 2. Procfile

Railway detecta automaticamente el `Procfile`:
```
web: python -m telegram_bot.bot
```

### 3. Deploy

```bash
git add .
git commit -m "feat: integrar telegram bot con motor cuantitativo"
git push origin main
```

Railway redeploya automaticamente al hacer push a main.

---

## Deploy Streamlit Cloud (dashboard)

Archivo principal: `streamlit_app.py`

Secrets en Streamlit Cloud → Settings → Secrets:
```toml
ODDS_API_KEY = "tu_key_aqui"
```

**Importante:** el nombre debe ser exactamente `ODDS_API_KEY` (case sensitive).

---

## HTTP 401 — Solucion

El error HTTP 401 en todos los escaneos significa que la API key
no llega al proceso. Checklist:

1. En Railway: verificar que `ODDS_API_KEY` este configurada en Variables
2. En Streamlit Cloud: verificar en Settings > Secrets
3. La key no debe tener espacios ni comillas extras
4. Verificar que la key este activa en https://the-odds-api.com/account

---

## Motor Matematico

```
P(Local)     = 1.56x + 46.47
P(Empate)    = -0.03x^2 - 0.29x + 29.48
P(Visitante) = 0.03x^2 - 1.27x + 23.65

x = suma de (goles L - goles V) ultimos 6 partidos del equipo

Edge = P(modelo) - P(implicita del mercado)
Value bet = Edge >= EDGE_MINIMO (default 3%)

Kelly = (b*p - q) / b
Stake = Kelly * Bankroll (cap 5%)
```

---

## Fuentes de Datos

- **Cuotas en tiempo real:** The Odds API (Pinnacle priority)
- **Estadisticas historicas:** football-data.co.uk (CSV por liga)
- **Timezone:** GMT-3 Argentina en todos los reportes
- 
