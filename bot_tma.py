import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set. Hardcoded fallbacks are prohibited.")

WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-atlas-app-services-url.com/") # Replace with deployed URL

# Setup
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Main menu with Web App button
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open VPN Dashboard 🚀", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text="Support 👨‍💻", url="https://t.me/Gl1ch555")]
    ])
    return keyboard

@dp.message(Command('start'))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"

    welcome_text = (
        f"👋 **Welcome, {username}!**\n\n"
        f"This bot is now a Telegram Mini App.\n"
        f"Click the button below to open your dashboard to:\n"
        f"- Check your balance and subscription\n"
        f"- Top up your balance\n"
        f"- Buy new VPN configurations\n"
        f"- View your active configurations"
    )

    await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

async def main():
    logging.info("Starting Telegram Mini App Bot...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
