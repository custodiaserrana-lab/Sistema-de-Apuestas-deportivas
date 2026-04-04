# =============================================================
# telegram_bot/bot.py
# Bot de Telegram para Futbol Quant Bot
# Integrado con main.py (motor cuantitativo)
# Deploy: Railway
# Custodia Serrana Lab 2026
# =============================================================

import os
import sys
import logging
import asyncio
from datetime import datetime, timezone, timedelta

# -- Path para importar main.py desde la raiz del repo --
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import main as motor
from telegram_bot.messages import (
    msg_bienvenida,
    msg_escaneando,
    msg_sin_resultados,
    msg_error_api,
    msg_value_bet,
    msg_resumen_scan,
    msg_estado,
    msg_ligas,
    ts_arg,
    LIGA_FLAGS,
)

# =============================================================
# CONFIGURACION
# =============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("FutbolQuantBot")

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ODDS_API_KEY     = os.environ.get("ODDS_API_KEY", "")
EDGE_MINIMO      = float(os.environ.get("EDGE_MINIMO", "3.0"))
HORAS_DEFAULT    = int(os.environ.get("HORAS_DEFAULT", "48"))
MAX_BETS_MSG     = int(os.environ.get("MAX_BETS_MSG", "15"))  # max bets por mensaje

# Affiliate link Melbet (configurable por env var)
MELBET_LINK = os.environ.get(
    "MELBET_LINK",
    "https://refmelbet.com/L?tag=d_XXXXXX"   # reemplaza con tu link real
)

if not TELEGRAM_TOKEN:
    log.critical("TELEGRAM_BOT_TOKEN no configurado. El bot no puede iniciar.")
    sys.exit(1)

# =============================================================
# INICIALIZACION
# =============================================================

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()

# =============================================================
# HELPER: ejecutar scan
# =============================================================

async def ejecutar_scan(horas: int) -> list:
    """
    Llama al motor principal (main.py) en un thread separado
    para no bloquear el event loop de asyncio.
    """
    if not ODDS_API_KEY:
        raise ValueError("ODDS_API_KEY no configurada")

    loop = asyncio.get_event_loop()

    def _run():
        todas = []
        for nombre, sport_key in motor.LIGAS_ODDS_API.items():
            url_stats = motor.LIGAS_STATS.get(nombre, "")
            try:
                apuestas = motor.analizar_liga(
                    nombre, sport_key, url_stats, ODDS_API_KEY, horas
                )
                todas.extend(apuestas)
            except Exception as e:
                log.warning(f"{nombre}: error en scan — {e}")
        return todas

    apuestas = await loop.run_in_executor(None, _run)
    # Ordenar por edge descendente
    apuestas.sort(key=lambda x: x.get("edge", 0), reverse=True)
    return apuestas


def footer_melbet() -> str:
    return f"\n\n_Apostá en_ [Melbet Argentina]({MELBET_LINK})"


# =============================================================
# HANDLERS
# =============================================================

@dp.message(Command("start", "ayuda", "help"))
async def cmd_start(msg: types.Message):
    await msg.answer(msg_bienvenida())


@dp.message(Command("ligas"))
async def cmd_ligas(msg: types.Message):
    await msg.answer(msg_ligas(motor.LIGAS_ODDS_API))


@dp.message(Command("estado"))
async def cmd_estado(msg: types.Message):
    api_ok = bool(ODDS_API_KEY)
    if api_ok:
        # Verificar conectividad real con un request minimo
        try:
            import requests
            r = requests.get(
                "https://api.the-odds-api.com/v4/sports",
                params={"apiKey": ODDS_API_KEY},
                timeout=5
            )
            api_ok = r.status_code == 200
        except Exception:
            api_ok = False

    texto = msg_estado(api_ok, len(motor.LIGAS_ODDS_API))
    await msg.answer(texto)


@dp.message(Command("scan"))
async def cmd_scan(msg: types.Message):
    await _scan_handler(msg, HORAS_DEFAULT)


@dp.message(Command("scan_12"))
async def cmd_scan_12(msg: types.Message):
    await _scan_handler(msg, 12)


@dp.message(Command("scan_24"))
async def cmd_scan_24(msg: types.Message):
    await _scan_handler(msg, 24)


@dp.message(Command("scan_72"))
async def cmd_scan_72(msg: types.Message):
    await _scan_handler(msg, 72)


@dp.message(Command("ranking"))
async def cmd_ranking(msg: types.Message):
    """Top 10 value bets por edge en ventana default."""
    await _scan_handler(msg, HORAS_DEFAULT, solo_ranking=True, top_n=10)


async def _scan_handler(msg: types.Message, horas: int,
                        solo_ranking: bool = False, top_n: int = None):
    """Handler compartido para todos los comandos de scan."""

    # Mensaje de espera
    wait_msg = await msg.answer(
        msg_escaneando(horas, len(motor.LIGAS_ODDS_API))
    )

    try:
        apuestas = await ejecutar_scan(horas)
    except ValueError:
        await wait_msg.delete()
        await msg.answer(msg_error_api())
        return
    except Exception as e:
        log.error(f"Error en scan: {e}")
        await wait_msg.delete()
        await msg.answer(f"Error inesperado: `{e}`")
        return

    await wait_msg.delete()

    if not apuestas:
        await msg.answer(msg_sin_resultados(horas))
        return

    # Limitar cantidad
    mostrar = apuestas[:top_n] if top_n else apuestas[:MAX_BETS_MSG]
    total   = len(apuestas)

    # Resumen
    await msg.answer(msg_resumen_scan(apuestas, horas))

    # Enviar cada bet como mensaje separado
    for i, ap in enumerate(mostrar, 1):
        texto = msg_value_bet(ap, rank=i if solo_ranking else None)
        texto += footer_melbet()
        try:
            await msg.answer(texto, disable_web_page_preview=True)
            await asyncio.sleep(0.3)   # evitar flood de Telegram
        except Exception as e:
            log.warning(f"Error enviando bet #{i}: {e}")

    # Pie con total si hay mas que no se mostraron
    if total > len(mostrar):
        restantes = total - len(mostrar)
        await msg.answer(
            f"_... y {restantes} bets mas. "
            f"Usa /scan con edge mas alto o consulta el dashboard._"
        )


# =============================================================
# ENTRADA PRINCIPAL
# =============================================================

async def main():
    log.info(f"Iniciando Futbol Quant Bot — {ts_arg()} ARG")
    log.info(f"Ligas: {len(motor.LIGAS_ODDS_API)} | Edge min: {EDGE_MINIMO}% | Horas default: {HORAS_DEFAULT}h")
    log.info(f"ODDS_API_KEY: {'configurada' if ODDS_API_KEY else 'NO CONFIGURADA'}")

    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())

