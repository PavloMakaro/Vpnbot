import logging
import os
import sys
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo
from aiogram.utils.markdown import hbold

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get token from env
TOKEN = os.getenv("BOT_TOKEN")

# Web App URL (hosted on Stitch or elsewhere)
# You must deploy your frontend to a static host (like Atlas App Services Hosting) and put the URL here.
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://example.com")

if not TOKEN:
    print("Error: BOT_TOKEN is not set. Please set it in environment variables.")
    # For testing purposes, you can uncomment this if you want to hardcode (not recommended)
    # TOKEN = "YOUR_TOKEN_HERE"

dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    kb = [
        [types.InlineKeyboardButton(text="🚀 Open VPN App", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)

    await message.answer(f"Hello, {hbold(message.from_user.full_name)}! \n\nManage your VPN subscription and configs in our Mini App.", reply_markup=keyboard)

async def main() -> None:
    if not TOKEN:
        return
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
