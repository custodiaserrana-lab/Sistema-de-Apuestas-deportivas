"""
config.py — Variables de entorno del Futbol Quant Bot
Custodia Serrana Lab © 2026

USO LOCAL (Termux/PC):
    Creá un archivo .env en la misma carpeta con:
        BOT_TOKEN=tu_token_aqui
        CHANNEL_ID=-100xxxxxxxxxx
        MELBET_LINK=https://melbet.com/...
        ADMIN_ID=tu_telegram_id

EN RAILWAY:
    Configurar en Variables del proyecto (no usar .env)
"""

import os
from dotenv import load_dotenv

load_dotenv()  # Carga .env si existe (desarrollo local)

# Token del bot — obtenido de @BotFather
BOT_TOKEN: str = os.environ["BOT_TOKEN"]

# ID del canal donde se publican los picks
# Formato: -100xxxxxxxxxx (con el -100 al inicio)
# Para obtenerlo: reenviá un mensaje del canal a @userinfobot
CHANNEL_ID: int = int(os.environ["CHANNEL_ID"])

# Tu link de afiliado Melbet Argentina
MELBET_LINK: str = os.environ.get(
    "MELBET_LINK",
    "https://melbet.com.ar/es/"  # reemplazar con tu link real de afiliado
)

# Tu Telegram ID (para comandos de admin)
# Para obtenerlo: mandá /start a @userinfobot
ADMIN_ID: int = int(os.environ.get("ADMIN_ID", "0"))
