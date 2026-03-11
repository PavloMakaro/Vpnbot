import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage

# Fetch from environment variables ONLY. No hardcoded tokens allowed.
BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL")

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    logging.error("BOT_TOKEN environment variable is not set. Exiting.")
    exit(1)

if not MINI_APP_URL:
    logging.error("MINI_APP_URL environment variable is not set. Exiting.")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть Mini App", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])

    await message.answer(
        "Добро пожаловать в VPN Bot!\n\n"
        "Для управления подпиской, пополнения баланса и получения конфигов нажмите кнопку ниже 👇",
        reply_markup=keyboard
    )

async def main():
    try:
        logging.info("Starting Telegram Mini App Bot...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
