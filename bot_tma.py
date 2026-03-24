import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

logging.basicConfig(level=logging.INFO)

# No hardcoded fallback, purely os.getenv per memory
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://your-atlas-app-url.com')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command('start'))
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open VPN App", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    await message.answer("Welcome to the VPN Mini App! Click below to open.", reply_markup=keyboard)

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is missing! Please set the BOT_TOKEN environment variable.")
        return
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
