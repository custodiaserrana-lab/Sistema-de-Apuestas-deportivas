import os, sys, logging, time, threading
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

import telebot
import main_bot as motor
from telegram_bot.messages import (
    msg_bienvenida, msg_escaneando, msg_sin_resultados,
    msg_error_api, msg_value_bet, msg_resumen_scan,
    msg_estado, msg_ligas, ts_arg,
)

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/bot.log")],
)
log = logging.getLogger("FQBot")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN","").strip()
ODDS_API_KEY   = os.environ.get("ODDS_API_KEY","").strip()
HORAS_DEFAULT  = int(os.environ.get("HORAS_DEFAULT","48"))
MAX_BETS_MSG   = int(os.environ.get("MAX_BETS_MSG","15"))
MELBET_LINK    = os.environ.get("MELBET_LINK","")

if not TELEGRAM_TOKEN:
    log.critical("TELEGRAM_BOT_TOKEN no configurado en .env")
    sys.exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="Markdown")

def footer():
    return f"\n\n_Aposta en_ [Melbet]({MELBET_LINK})" if MELBET_LINK else ""

def ejecutar_scan(horas):
    if not ODDS_API_KEY:
        raise ValueError("ODDS_API_KEY no configurada")
    todas = []
    for nombre, sport_key in motor.LIGAS_ODDS_API.items():
        try:
            apuestas = motor.analizar_liga(
                nombre, sport_key,
                motor.LIGAS_STATS.get(nombre,""),
                ODDS_API_KEY, horas)
            todas.extend(apuestas)
        except Exception as e:
            log.warning(f"{nombre}: {e}")
    todas.sort(key=lambda x: x.get("edge",0), reverse=True)
    return todas

def scan_handler(msg, horas, top_n=None, con_rank=False):
    wait = bot.send_message(msg.chat.id,
        msg_escaneando(horas, len(motor.LIGAS_ODDS_API)))
    try:
        apuestas = ejecutar_scan(horas)
    except ValueError:
        bot.delete_message(msg.chat.id, wait.message_id)
        bot.send_message(msg.chat.id, msg_error_api())
        return
    except Exception as e:
        bot.delete_message(msg.chat.id, wait.message_id)
        bot.send_message(msg.chat.id, f"Error: `{e}`")
        return

    bot.delete_message(msg.chat.id, wait.message_id)

    if not apuestas:
        bot.send_message(msg.chat.id, msg_sin_resultados(horas))
        return

    mostrar = apuestas[: top_n or MAX_BETS_MSG]
    bot.send_message(msg.chat.id, msg_resumen_scan(apuestas, horas))

    for i, ap in enumerate(mostrar, 1):
        try:
            bot.send_message(msg.chat.id,
                msg_value_bet(ap, rank=i if con_rank else None) + footer(),
                disable_web_page_preview=True)
            time.sleep(0.35)
        except Exception as e:
            log.warning(f"Bet #{i}: {e}")

    sobrantes = len(apuestas) - len(mostrar)
    if sobrantes > 0:
        bot.send_message(msg.chat.id,
            f"_... y {sobrantes} bets mas. Usa /ranking._")

@bot.message_handler(commands=["start","ayuda","help"])
def cmd_start(msg):
    bot.send_message(msg.chat.id, msg_bienvenida())

@bot.message_handler(commands=["ligas"])
def cmd_ligas(msg):
    bot.send_message(msg.chat.id, msg_ligas(motor.LIGAS_ODDS_API))

@bot.message_handler(commands=["estado"])
def cmd_estado(msg):
    import requests as req
    api_ok = False
    if ODDS_API_KEY:
        try:
            r = req.get("https://api.the-odds-api.com/v4/sports",
                        params={"apiKey": ODDS_API_KEY}, timeout=6)
            api_ok = r.status_code == 200
        except Exception:
            pass
    bot.send_message(msg.chat.id, msg_estado(api_ok, len(motor.LIGAS_ODDS_API)))

@bot.message_handler(commands=["scan"])
def cmd_scan(msg):
    threading.Thread(target=scan_handler, args=(msg, HORAS_DEFAULT)).start()

@bot.message_handler(commands=["scan_12"])
def cmd_scan_12(msg):
    threading.Thread(target=scan_handler, args=(msg, 12)).start()

@bot.message_handler(commands=["scan_24"])
def cmd_scan_24(msg):
    threading.Thread(target=scan_handler, args=(msg, 24)).start()

@bot.message_handler(commands=["scan_72"])
def cmd_scan_72(msg):
    threading.Thread(target=scan_handler, args=(msg, 72)).start()

@bot.message_handler(commands=["ranking"])
def cmd_ranking(msg):
    threading.Thread(target=scan_handler,
        args=(msg, HORAS_DEFAULT), kwargs={"top_n":10,"con_rank":True}).start()

if __name__ == "__main__":
    log.info(f"=== Futbol Quant Bot -- {ts_arg()} ARG ===")
    log.info(f"API key: {'OK' if ODDS_API_KEY else 'FALTA'}")
    log.info("Bot iniciado. Esperando mensajes...")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=25)
        except Exception as e:
            log.error(f"Desconexion: {e} -- reintentando en 15s")
            time.sleep(15)
