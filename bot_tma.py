import os
import sys
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo
from aiogram.client.default import DefaultBotProperties

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get BOT_TOKEN from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: BOT_TOKEN environment variable not set.")
    sys.exit(1)

# Set up the Web App URL (replace with actual deployed URL later, or local URL for testing)
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://example.com") # Should be provided via env

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Handle the /start command.
    Sends a message with an inline keyboard containing a button to open the Web App.
    """
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Open VPN App", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    await message.answer("Welcome to the VPN Bot! Click the button below to open the app.", reply_markup=keyboard)

async def main():
    """
    Main entry point for the bot.
    """
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
