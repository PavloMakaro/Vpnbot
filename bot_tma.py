import os
import sys
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Configure logging
logging.basicConfig(level=logging.INFO)

# Setup Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logging.error("BOT_TOKEN environment variable is not set. Exiting.")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# URL of the hosted Web App (e.g., GitHub Pages, Vercel, or your own server)
# During development, this can be an ngrok URL pointing to your local server
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com/frontend/index.html")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Handle the /start command.
    Sends a welcome message with an inline button to open the Mini App.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚀 Открыть личный кабинет VPN",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]
    ])

    welcome_text = (
        "👋 Добро пожаловать в VPN Bot!\n\n"
        "Для управления подпиской, покупки VPN и просмотра ваших конфигов, "
        "нажмите кнопку ниже, чтобы открыть личный кабинет."
    )

    await message.answer(welcome_text, reply_markup=keyboard)

async def main():
    """Start polling."""
    logging.info("Starting bot...")
    # Drop pending updates to avoid processing old messages
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")