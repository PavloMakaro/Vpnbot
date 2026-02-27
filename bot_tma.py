import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
from aiogram.filters import Command

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Web App URL (This should be the URL where your frontend is hosted)
WEB_APP_URL = "https://<your-app-id>.mongodbstitch.com"

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    """
    This handler receives messages with `/start` command
    """
    kb = [
        [types.KeyboardButton(text="Open VPN App 🚀", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer(
        "Welcome to the VPN Bot! Click the button below to manage your subscription.",
        reply_markup=keyboard
    )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
