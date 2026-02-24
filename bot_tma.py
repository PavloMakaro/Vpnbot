import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Configuration
# Replace with your actual token and Web App URL
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://<your-app-id>.mongodbstitch.com/")

# Initialize Bot and Dispatcher
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    """
    This handler receives messages with `/start` command
    """
    user_name = message.from_user.full_name

    # Check for referral parameter
    args = message.text.split()
    referral_param = args[1] if len(args) > 1 else None

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Open VPN App", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

    welcome_text = (
        f"Hello, {user_name}!\n\n"
        "Welcome to the **VPN Bot Mini App**.\n"
        "Manage your subscription, buy configs, and top up your balance directly here."
    )

    if referral_param:
        welcome_text += f"\n\n(Referral code detected: {referral_param})"

    await message.answer(welcome_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

async def main():
    if TOKEN == "YOUR_BOT_TOKEN":
        print("Please set your BOT_TOKEN environment variable or edit bot_tma.py")
        return

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
