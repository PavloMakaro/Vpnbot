import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

logging.basicConfig(level=logging.INFO)

# Hardcoded fallback for BOT_TOKEN is explicitly prohibited. Must use env var.
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

WEBAPP_URL = os.getenv("WEBAPP_URL")

if not WEBAPP_URL:
    raise ValueError("WEBAPP_URL environment variable is not set")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open VPN App", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

    await message.answer(
        "Welcome to the VPN Mini App!\nClick the button below to open the app.",
        reply_markup=markup
    )

async def main() -> None:
    print("Starting Telegram TMA Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())