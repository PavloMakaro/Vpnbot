import telebot
from telebot import types
import os

# Configuration
TOKEN = os.getenv("BOT_TOKEN", '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY')
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-webapp-url.com") # User needs to set this

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    # Mini App Button
    webApp = types.WebAppInfo(WEBAPP_URL)
    markup.add(types.InlineKeyboardButton("🚀 Open VPN App", web_app=webApp))

    # Optional: Admin button if needed, but better inside the app or separate command
    # markup.add(types.InlineKeyboardButton("Help", callback_data="help"))

    bot.send_message(
        message.chat.id,
        "👋 **Welcome to VPN Bot!**\n\n"
        "Manage your subscription, top up balance, and get high-speed VPN access directly in our Mini App.\n\n"
        "Click the button below to start:",
        parse_mode='Markdown',
        reply_markup=markup
    )

    # Also set the Menu Button
    bot.set_chat_menu_button(
        message.chat.id,
        types.MenuButtonWebApp(type="web_app", text="Open App", web_app=webApp)
    )

@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    # Handle data sent back from Web App if any
    print(f"Received data: {message.web_app_data.data}")

if __name__ == "__main__":
    print(f"Bot started. WebApp URL: {WEBAPP_URL}")
    bot.infinity_polling()
