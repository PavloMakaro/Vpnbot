import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get BOT_TOKEN from environment variable (Do not hardcode fallbacks as per memory)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Get Web App URL from environment variable
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://example.com/miniapp") # Replace default in production

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Handle the /start command.
    Sends a welcome message with a button to open the Web App.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open VPN App 🚀",
                    web_app=WebAppInfo(url=WEB_APP_URL)
                )
            ]
        ]
    )

    welcome_text = (
        "👋 Welcome to the VPN Bot!\n\n"
        "Click the button below to open the Mini App and manage your VPN subscription."
    )

    await message.answer(welcome_text, reply_markup=keyboard)

async def main():
    """Start the bot."""
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())