import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.client.default import DefaultBotProperties

# Configure logging
logging.basicConfig(level=logging.INFO)

# Token from environment variable or placeholder
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app-url.vercel.app") # Replace with your deployed URL

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    """
    This handler receives messages with `/start` command
    """
    kb = [
        [
            types.InlineKeyboardButton(text="Open VPN App 🚀", web_app=WebAppInfo(url=WEBAPP_URL))
        ]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)

    await message.answer(f"Hello, {message.from_user.full_name}! 👋\n\nClick the button below to manage your VPN subscription.", reply_markup=keyboard)

async def main():
    # Set the menu button to open the Web App
    await bot.set_chat_menu_button(
        menu_button=types.MenuButtonWebApp(text="Open App", web_app=WebAppInfo(url=WEBAPP_URL))
    )

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
