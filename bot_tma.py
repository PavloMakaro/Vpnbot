import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
# Ensure you do NOT hardcode the real token in production.
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com") # Replace with the URL where your frontend is hosted

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    """
    Handler for the /start command.
    Sends a welcome message with a button to open the Web App.
    """
    user_name = message.from_user.first_name

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть VPN Bot 🚀", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

    welcome_text = (
        f"Привет, {user_name}! 👋\n\n"
        "Добро пожаловать в VPN Bot.\n"
        "Нажмите кнопку ниже, чтобы открыть приложение, пополнить баланс и приобрести подписку."
    )

    await message.answer(welcome_text, reply_markup=keyboard)

async def main():
    """Main execution function"""
    logging.info("Starting Telegram Bot for TMA...")

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logging.warning("BOT_TOKEN is not set properly! Please set the BOT_TOKEN environment variable.")

    if WEBAPP_URL == "https://your-domain.com":
        logging.warning("WEBAPP_URL is using the default placeholder! Please set it to your actual frontend URL.")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())