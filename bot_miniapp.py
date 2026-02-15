import telebot
from telebot import types
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("Error: BOT_TOKEN environment variable not set.")
    exit(1)

WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-frontend-url.com") # User needs to change this

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Open VPN App", web_app=types.WebAppInfo(url=WEB_APP_URL)))

    bot.send_message(
        message.chat.id,
        "👋 Welcome to the VPN Service!\n\n"
        "Tap the button below to manage your subscription, check balance, and get your VPN configs.",
        reply_markup=markup
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(
        message.chat.id,
        "To use this bot, please open the Mini App by typing /start."
    )

print("Bot is running...")
bot.infinity_polling()
