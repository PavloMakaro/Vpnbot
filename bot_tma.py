import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

WEB_APP_URL = os.getenv("WEB_APP_URL", "https://vpn-bot-tma-xxxxx.mongodbstitch.com") # Replace with your actual App Services hosting URL

# Initialize
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Send a welcome message with a button to launch the Web App.
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Open VPN App", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text="Support", url="https://t.me/Gl1ch555")]
    ])

    await message.answer(
        "👋 Welcome to the VPN Bot Mini App!\n\n"
        "Manage your subscription, top up balance, and get your VPN config directly in the app.",
        reply_markup=markup
    )

async def main():
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
