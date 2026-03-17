import os
import sys
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
import asyncio

logging.basicConfig(level=logging.INFO)

# No hardcoded fallback, purely from env
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logging.error("BOT_TOKEN environment variable not set. Exiting.")
    sys.exit(1)

# Ensure TMA_URL is provided for the WebApp
TMA_URL = os.getenv('TMA_URL', 'https://your-domain.com') # Fallback for local testing, but should be set in prod

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="Открыть VPN Mini App 🚀",
        web_app=WebAppInfo(url=TMA_URL)
    ))

    welcome_text = (
        "👋 Добро пожаловать в VPN сервис!\n\n"
        "Нажмите кнопку ниже, чтобы открыть приложение для покупки подписки и управления конфигурациями."
    )

    await message.answer(welcome_text, reply_markup=builder.as_markup())

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
