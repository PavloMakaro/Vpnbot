import telebot
from telebot import types
import time
import logging
import os

# Configuration
# Use environment variables for sensitive data
TOKEN = os.getenv('BOT_TOKEN', '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY')
WEB_APP_URL = os.getenv('WEB_APP_URL', "https://example.com") # REPLACE WITH YOUR ACTUAL DEPLOYED MINI APP URL

# Setup logging
logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_name = message.from_user.first_name

        markup = types.InlineKeyboardMarkup()
        web_app_info = types.WebAppInfo(url=WEB_APP_URL)
        markup.add(types.InlineKeyboardButton("🚀 Open VPN App", web_app=web_app_info))

        bot.send_message(
            message.chat.id,
            f"👋 Hello, {user_name}!\n\n"
            "Welcome to the VPN Bot. Manage your subscription, top up balance, and get high-speed VPN configs directly in our Mini App!",
            reply_markup=markup
        )

        # Also set the menu button (persistent)
        bot.set_chat_menu_button(
            message.chat.id,
            types.MenuButtonWebApp(type="web_app", text="Open App", web_app=web_app_info)
        )

    except Exception as e:
        logging.error(f"Error in start command: {e}")

@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    # Handle data sent back from Mini App if any (usually not needed for this architecture)
    pass

if __name__ == "__main__":
    print("Bot is running...")
    # Set default menu button for all users
    try:
        bot.set_chat_menu_button(
            menu_button=types.MenuButtonWebApp(type="web_app", text="Open App", web_app=types.WebAppInfo(url=WEB_APP_URL))
        )
    except Exception as e:
        print(f"Failed to set menu button: {e}")

    bot.infinity_polling()
