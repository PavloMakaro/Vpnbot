import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is not set.")
        sys.exit(1)

    web_app_url = os.getenv("WEB_APP_URL", "https://example.com") # Replace with your actual Web App URL

    bot = Bot(token=bot_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def command_start_handler(message: types.Message) -> None:
        """
        This handler receives messages with `/start` command
        """
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Open VPN App 🚀",
                        web_app=WebAppInfo(url=web_app_url)
                    )
                ]
            ]
        )
        await message.answer(
            f"Hello, {message.from_user.full_name}! 👋\n\nClick the button below to open the VPN App.",
            reply_markup=markup
        )

    # Start polling
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
