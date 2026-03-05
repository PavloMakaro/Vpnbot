import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Ensure BOT_TOKEN is present
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logging.error("BOT_TOKEN environment variable is not set. Exiting.")
    sys.exit(1)

# URL of the hosted Mini App (e.g., GitHub Pages, Cloudflare Pages)
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://your-domain.com/frontend')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_webapp_keyboard(start_param: str = None) -> InlineKeyboardMarkup:
    """Generate keyboard with WebApp button."""
    url = WEBAPP_URL
    if start_param:
        url += f"?startapp={start_param}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Open VPN Store 🚀",
            web_app=WebAppInfo(url=url)
        )]
    ])
    return keyboard

@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    """Handle /start command and provide the Mini App button."""
    start_param = command.args

    welcome_text = (
        "👋 Welcome to the VPN Bot!\n\n"
        "To purchase a subscription, check your balance, or manage your configs, "
        "please open the Mini App below 👇"
    )

    await message.answer(
        welcome_text,
        reply_markup=get_webapp_keyboard(start_param)
    )

async def main():
    logging.info("Starting TMA bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")