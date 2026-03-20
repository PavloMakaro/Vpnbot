import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

load_dotenv()

# We strictly avoid hardcoding BOT_TOKEN, but the memory states:
# "Hardcoded fallbacks for BOT_TOKEN in bot_tma.py are explicitly prohibited."
# So we must get it from the environment variable.
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Handle the /start command.
    Sends a welcome message with an inline keyboard button to launch the Telegram Mini App.
    """
    web_app_url = os.getenv('WEB_APP_URL', 'https://your-web-app-url.com') # Fallback for local testing, though in production it should be set

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open VPN App 🚀", web_app=WebAppInfo(url=web_app_url))]
    ])

    await message.answer(
        "Welcome to the VPN Bot! 🚀\n\nClick the button below to open the Mini App and manage your VPN subscriptions.",
        reply_markup=markup
    )

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set in environment variables.")
        return

    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
