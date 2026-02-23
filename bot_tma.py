import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import MenuButtonWebApp, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot
# For security, use environment variables.
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN env variable not set. Please set it.")
    sys.exit(1)

# This URL must be the URL where you hosted the frontend (e.g., MongoDB Atlas App Hosting URL)
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://<your-app-id>.mongodbstitch.com")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Open VPN App 📱", web_app=WebAppInfo(url=WEBAPP_URL))]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await message.answer(
        "👋 **Welcome to VPN Bot!**\n\n"
        "Manage your subscription, top up balance, and get VPN configs directly in the Mini App.\n\n"
        "👇 Click the button below to start!",
        reply_markup=kb,
        parse_mode="Markdown"
    )

    # Try to set the menu button for the chat
    try:
        await bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(text="Open App", web_app=WebAppInfo(url=WEBAPP_URL))
        )
    except Exception as e:
        logging.error(f"Failed to set menu button: {e}")

async def main():
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
