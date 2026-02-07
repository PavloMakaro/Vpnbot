import telebot
from telebot import types
import os

# Configuration
# SECURITY: Do not hardcode your token here! Use environment variables.
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
APP_URL = os.getenv("APP_URL", "https://your-stitch-app-url.mongodbstitch.com") # Replace with your deployed frontend URL

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    # The Mini App button
    mini_app_button = types.InlineKeyboardButton(
        text="Open VPN App 🚀",
        web_app=types.WebAppInfo(url=APP_URL)
    )
    markup.add(mini_app_button)

    bot.send_message(
        message.chat.id,
        "👋 **Welcome to VPN Mini App!**\n\n"
        "Manage your subscription, top up balance, and get your VPN configs directly in our new Mini App.",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    # Handle data sent back from the Mini App if any (usually not needed for this flow)
    print(f"Received data: {message.web_app_data.data}")

if __name__ == "__main__":
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Error: Please set the BOT_TOKEN environment variable or edit the script.")
    else:
        print("Bot is running...")
        bot.infinity_polling()
