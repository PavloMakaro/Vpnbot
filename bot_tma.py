import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.exceptions import TelegramAPIError

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fetch Token from environment, forbid hardcoded fallbacks per guidelines
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("FATAL ERROR: BOT_TOKEN environment variable is not set. Hardcoded fallbacks are prohibited.")
    sys.exit(1)

WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-hosting-provider.com/index.html") # Replace in production

# Initialize Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_main_menu_keyboard(start_param: str = None) -> InlineKeyboardMarkup:
    """
    Creates an inline keyboard with a WebApp button.
    Passes the `start_param` (referral code) to the WebApp URL if provided.
    """
    url = WEB_APP_URL

    # Passing the referral parameter to the TMA
    if start_param:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}start_param={start_param}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть VPN Mini App", web_app=WebAppInfo(url=url))],
        [InlineKeyboardButton(text="🤝 Поддержка", url="https://t.me/Gl1ch555")]
    ])
    return keyboard

@dp.message(Command('start'))
async def start_handler(message: types.Message, command: Command = None):
    """
    Handles the /start command.
    Captures any referral code passed via the start command (e.g., /start 12345)
    and passes it down to the Mini App.
    """
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Пользователь"

    # Extract referral code if present
    start_param = None
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        start_param = args[1]
        logger.info(f"User {user_id} started bot with referral code: {start_param}")

    welcome_text = (
        f"👋 Добро пожаловать, {first_name}!\n\n"
        f"🔐 Ваш личный VPN сервис теперь доступен в удобном формате Mini App.\n\n"
        f"Здесь вы можете:\n"
        f"💳 Пополнять баланс\n"
        f"📦 Покупать подписки\n"
        f"🔑 Получать конфигурации\n"
        f"🤝 Участвовать в реферальной программе\n\n"
        f"👇 Нажмите кнопку ниже, чтобы открыть приложение:"
    )

    try:
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(start_param=start_param)
        )
    except TelegramAPIError as e:
        logger.error(f"Failed to send start message to {user_id}: {e}")

async def main():
    logger.info("Starting Telegram Bot for Mini App...")

    # Drop pending updates to avoid processing old messages upon restart
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped gracefully.")