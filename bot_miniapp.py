import telebot
from telebot import types
import os

# Configuration
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://<your-app-id>.mongodbstitch.com/") # Replace with your actual Web App URL

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(url=WEB_APP_URL)
    markup.add(types.InlineKeyboardButton("Open VPN App 🚀", web_app=web_app))

    bot.send_message(
        message.chat.id,
        "Welcome to the VPN Mini App! Click the button below to manage your subscription.",
        reply_markup=markup
    )

@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    # Handle data sent back from the Web App if any
    print(f"Received data from WebApp: {message.web_app_data.data}")
    bot.send_message(message.chat.id, f"Received: {message.web_app_data.data}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
