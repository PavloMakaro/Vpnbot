import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Configure logging
logging.basicConfig(level=logging.INFO)

# Fetch Bot Token from environment variables (no hardcoded fallback)
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set.")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Provide the URL of your Web App (e.g. deployed on Vercel, Netlify, or self-hosted)
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://example.com") # Replace with your actual Web App URL

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Handle the /start command.
    Sends a welcome message with an inline button to open the Telegram Mini App.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open VPN App 🚀", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])

    await message.answer(
        "Welcome to the VPN Bot! 🚀\n\n"
        "Click the button below to open the Mini App and manage your subscriptions, configs, and balance.",
        reply_markup=keyboard
    )

async def main():
    """
    Start polling.
    """
    logging.info("Starting bot_tma.py...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
