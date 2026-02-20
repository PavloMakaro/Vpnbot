import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Configure logging
logging.basicConfig(level=logging.INFO)

# Token from environment variable or hardcoded (placeholder)
# Replace with your actual bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY")

# Web App URL (User needs to replace this with their Atlas App Hosting URL)
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://replace-with-your-atlas-app-url.mongodbstitch.com")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start(message: types.Message):
    # Determine if there's a referral parameter
    # The Web App will read this from initDataUnsafe.start_param automatically

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Open VPN App", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text="Support", url="https://t.me/Gl1ch555")]
    ])

    await message.answer(
        "Welcome to the VPN Bot! 🛡️\n\n"
        "Manage your subscription, top up balance, and get high-speed VPN configs directly in the Mini App.",
        reply_markup=kb
    )

async def main():
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")
