# Sistema de Apuestas Deportivas — Futbol Quant Bot

**Custodia Serrana Lab 2026**

SaaS de analisis cuantitativo de futbol con deteccion de value betting.

---

## Stack

| Componente | Tecnologia | Deploy |
|------------|------------|--------|
| Dashboard web | Streamlit | Streamlit Cloud |
| Bot Telegram | aiogram v3 | Railway |
| Motor cuantitativo | Python + pandas | — |
| Cuotas en tiempo real | The Odds API | — |
| Estadisticas historicas | football-data.co.uk | — |

---

## Estructura

```
├── main.py              # Motor live (The Odds API + ratings)
├── app.py               # Motor backtesting (football-data.co.uk)
├── streamlit_app.py     # Dashboard web
├── telegram_bot/
│   ├── bot.py           # Bot Telegram (aiogram v3)
│   └── messages.py      # Templates de mensajes
├── config/
│   └── ligas.yaml       # Configuracion de ligas
├── requirements.txt     # Dependencias
├── Procfile             # Railway
└── docs/
    └── TELEGRAM_BOT.md  # Documentacion bot
```

---

## Variables de Entorno

| Variable | Descripcion | Obligatorio |
|----------|-------------|-------------|
| `ODDS_API_KEY` | API key de the-odds-api.com | Si |
| `TELEGRAM_BOT_TOKEN` | Token del bot (@BotFather) | Para bot |
| `EDGE_MINIMO` | Edge minimo % (default 3.0) | No |
| `HORAS_DEFAULT` | Ventana en horas (default 48) | No |
| `MAX_BETS_MSG` | Max bets por mensaje (default 15) | No |
| `MELBET_LINK` | Link afiliado Melbet | No |

---

## Deploy rapido

```bash
# 1. Clonar
git clone https://github.com/custodiaserrana-lab/Sistema-de-Apuestas-deportivas

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables
cp .env.example .env
# editar .env con tus keys

# 4. Ejecutar dashboard
streamlit run streamlit_app.py

# 5. Ejecutar bot (en otro terminal)
python -m telegram_bot.bot
```

Ver [docs/TELEGRAM_BOT.md](docs/TELEGRAM_BOT.md) para deployment en Railway y Streamlit Cloud.

---

## Motor Matematico

```
P(Local)     = 1.56x + 46.47
P(Empate)    = -0.03x^2 - 0.29x + 29.48
P(Visitante) = 0.03x^2 - 1.27x + 23.65

x = rating diferencial (ultimos 6 partidos)
Edge = P(modelo) - P(implicita mercado)
```

---

*Las apuestas deportivas implican riesgo economico. Sistema para uso de analisis cuantitativo.*
