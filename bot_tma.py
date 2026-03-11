import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load configuration from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")

if not BOT_TOKEN:
    logging.error("BOT_TOKEN environment variable is not set!")
    sys.exit(1)

if not WEB_APP_URL:
    logging.warning("WEB_APP_URL environment variable is not set. The Web App button will not work correctly.")

# Initialize Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Simulate "Thinking" or "Typing" action for better UX
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(1) # Short delay to make it feel natural

    # Create the Web App button
    url = WEB_APP_URL if WEB_APP_URL else "https://telegram.org"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open VPN App 🚀", web_app=WebAppInfo(url=url))]
    ])

    await message.answer(
        "👋 **Welcome to VPN Bot!**\n\n"
        "Your secure connection starts here.\n"
        "Manage your subscription, balance, and configs directly in our Mini App.",
        parse_mode="Markdown",
        reply_markup=markup
    )

async def main() -> None:
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.info("Starting bot...")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
