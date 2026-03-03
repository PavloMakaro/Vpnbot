import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://your-domain.com/index.html') # Need to be set in production

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_webapp_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть VPN Mini App 🚀", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    return markup

@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в VPN Bot!\n\n"
        "Теперь мы работаем в формате удобного Telegram Mini App. "
        "Нажмите кнопку ниже, чтобы открыть личный кабинет, пополнить баланс и получить конфиги.",
        reply_markup=get_webapp_keyboard()
    )

async def main():
    logging.info("Starting TMA Bot...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())