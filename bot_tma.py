import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from motor.motor_asyncio import AsyncIOMotorClient

# Configuration
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://YOUR_MONGO_URI")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-app-id.mongodbstitch.com") # Replace with your Stitch App URL
ADMIN_ID = int(os.getenv("ADMIN_ID", "8320218178"))

# Logging
logging.basicConfig(level=logging.INFO)

# Initialize
bot = Bot(token=TOKEN)
dp = Dispatcher()

# MongoDB
client = AsyncIOMotorClient(MONGO_URI)
db = client.vpn_bot
users_collection = db.users
configs_collection = db.configs

# --- Handlers ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    """
    Entry point. Sends the Menu Button to open the Mini App.
    """
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Open VPN App", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])

    await message.answer(
        "👋 Welcome to the VPN Bot!\n\n"
        "Click the button below to manage your subscription, buy VPN, and top up your balance.",
        reply_markup=kb
    )

@dp.message(Command("admin_help"))
async def admin_help(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "🛠 **Admin Commands**\n\n"
        "/add_config <period> <link> - Add a single config\n"
        "/stats - Show basic stats"
    )

@dp.message(Command("add_config"))
async def add_config(message: types.Message):
    """
    Usage: /add_config 1_month vless://...
    """
    if message.from_user.id != ADMIN_ID:
        return

    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("Usage: /add_config <period> <link>")
            return

        period = parts[1]
        link = parts[2]

        # Insert into DB
        result = await configs_collection.insert_one({
            "period": period,
            "link": link,
            "used": False,
            "name": f"Config {period}",
            "created_at": message.date
        })

        await message.answer(f"✅ Config added! ID: {result.inserted_id}")

    except Exception as e:
        await message.answer(f"❌ Error: {e}")

@dp.message(Command("stats"))
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    user_count = await users_collection.count_documents({})
    config_count = await configs_collection.count_documents({})
    unused_configs = await configs_collection.count_documents({"used": False})

    await message.answer(
        f"📊 **Stats**\n"
        f"Users: {user_count}\n"
        f"Total Configs: {config_count}\n"
        f"Available Configs: {unused_configs}"
    )

async def main():
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
