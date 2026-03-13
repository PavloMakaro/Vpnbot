import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO)

# Hardcoded fallback prohibited, using environment variable exclusively
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logging.error("BOT_TOKEN environment variable not set.")
    sys.exit(1)

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com/webapp")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    kb = [
        [
            types.KeyboardButton(
                text="Open VPN App",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True
    )

    await message.answer(
        f"Hello, {message.from_user.full_name}! Click the button below to open the VPN App.",
        reply_markup=keyboard
    )

async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
