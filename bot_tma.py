import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from motor.motor_asyncio import AsyncIOMotorClient

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGODB_URI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-frontend-url.com")

if not BOT_TOKEN:
    print("Error: BOT_TOKEN is not set.")
    sys.exit(1)

# Initialize Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# MongoDB Connection
mongo_client = None
db = None

async def init_mongo():
    global mongo_client, db
    if not MONGO_URI:
        logging.warning("MONGODB_URI not set. Admin commands may fail.")
        return
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    db = mongo_client['vpn_bot']
    logging.info("Connected to MongoDB")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Send a message with a button to open the Mini App.
    """
    kb = [
        [types.InlineKeyboardButton(text="🚀 Open VPN App", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)

    await message.answer(
        "Welcome! Click the button below to manage your VPN subscription.",
        reply_markup=keyboard
    )

@dp.message(Command("admin_add_config"))
async def cmd_add_config(message: types.Message):
    """
    Usage: /admin_add_config <period_key> <link1> <link2> ...
    Example: /admin_add_config 1_month vmess://... vless://...
    """
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: /admin_add_config <period> <link1> [link2 ...]")
        return

    period = parts[1]
    links = parts[2:]

    if not db:
        await message.answer("Database not connected.")
        return

    configs_col = db['configs']
    count = 0

    # Batch insert
    documents = []
    for link in links:
        documents.append({
            "period": period,
            "link": link,
            "used": False,
            "created_at": message.date
        })

    if documents:
        result = await configs_col.insert_many(documents)
        count = len(result.inserted_ids)

    await message.answer(f"Added {count} configs for period '{period}'.")

@dp.message(Command("admin_stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not db:
        await message.answer("Database not connected.")
        return

    users_count = await db['users'].count_documents({})
    payments_count = await db['payments'].count_documents({'status': 'succeeded'})

    await message.answer(
        f"📊 **Stats:**\n"
        f"Users: {users_count}\n"
        f"Successful Payments: {payments_count}"
    )

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_mongo()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
