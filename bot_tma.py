import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Configure logging
logging.basicConfig(level=logging.INFO)

# Fetch bot token from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")

# Fetch Web App URL from environment variables
WEB_APP_URL = os.getenv("WEB_APP_URL")
if not WEB_APP_URL:
    raise ValueError("WEB_APP_URL environment variable not set")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """
    This handler receives messages with `/start` command
    and displays the Web App button.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Open VPN App 🚀",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]
    ])

    welcome_text = (
        f"👋 Hello, {message.from_user.first_name}!\n\n"
        "Welcome to the VPN Mini App.\n"
        "Click the button below to manage your VPN subscriptions and configs."
    )

    await message.answer(welcome_text, reply_markup=keyboard)

async def main() -> None:
    """Entry point"""
    logging.info("Starting Telegram Mini App Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
