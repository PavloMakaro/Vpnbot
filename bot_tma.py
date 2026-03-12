import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is missing")

WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-domain.com/index.html")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_main_menu(user_id=None, referred_by=None):
    # Pass parameters to web app via URL query (if needed, though initData is better)
    url = f"{WEB_APP_URL}?start_param={referred_by}" if referred_by else WEB_APP_URL
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть Личный Кабинет", web_app=WebAppInfo(url=url))],
        [InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/Gl1ch555")]
    ])
    return keyboard

@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    args = message.text.split()
    referred_by = args[1] if len(args) > 1 else None

    welcome_text = (
        f"👋 Добро пожаловать, {message.from_user.first_name}!\n\n"
        f"🛡 Это официальный VPN-бот.\n"
        f"Нажмите кнопку ниже, чтобы открыть личный кабинет, пополнить баланс и приобрести подписку."
    )

    await message.answer(welcome_text, reply_markup=get_main_menu(message.from_user.id, referred_by))

async def main():
    print("Запуск TMA бота...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())