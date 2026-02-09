import telebot
from telebot import types
import time

# TOKEN from ai_studio_code.py
TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY'

# PLACEHOLDER: The user must deploy the frontend and put the URL here
# Example: "https://your-username.github.io/repo-name/" or Realm App Hosting URL
WEB_APP_URL = "https://example.com/vpn-mini-app"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    Sends a welcome message with a button to open the Mini App.
    """
    markup = types.InlineKeyboardMarkup()
    # Create a WebAppInfo object with the URL
    web_app = types.WebAppInfo(url=WEB_APP_URL)

    # Add a button that launches the Web App
    markup.add(types.InlineKeyboardButton("🚀 Open VPN App", web_app=web_app))

    bot.send_message(
        message.chat.id,
        "🎉 **Welcome to the VPN Bot Mini App!**\n\n"
        "We have moved to a new convenient interface.\n"
        "Manage your subscription, top up balance, and get configs instantly.",
        parse_mode='Markdown',
        reply_markup=markup
    )

    # Attempt to set the persistent Menu Button for this chat
    try:
        bot.set_chat_menu_button(
            message.chat.id,
            types.MenuButtonWebApp("Open App", web_app)
        )
    except Exception as e:
        print(f"Failed to set menu button: {e}")

if __name__ == "__main__":
    print(f"Bot started with Web App URL: {WEB_APP_URL}")
    print("Please update WEB_APP_URL in bot_miniapp.py with your actual frontend URL.")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot stopped: {e}")
