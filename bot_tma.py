import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    await message.answer("Добро пожаловать в VPN Bot! Нажмите кнопку ниже, чтобы открыть приложение.", reply_markup=markup)

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set.")
        return
    if not WEBAPP_URL:
        logging.error("WEBAPP_URL is not set.")
        return
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
