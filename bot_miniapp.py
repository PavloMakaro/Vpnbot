import telebot
from telebot import types
import os

# Configuration
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://<your-app-id>.mongodbstitch.com/") # Replace with your deployed App Services URL

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Check for referral parameter
    # The referral logic is now handled inside the Web App via initData.start_param
    # But we can also acknowledge it here if needed.

    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🚀 Open VPN App", web_app=types.WebAppInfo(url=WEBAPP_URL))
    markup.add(btn)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to the VPN Bot!\n\n"
        "Click the button below to open the Mini App, manage your subscription, and buy configs.",
        reply_markup=markup
    )

    # Set the Menu Button as well
    try:
        bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=types.MenuButtonWebApp(type="web_app", text="Open App", web_app=types.WebAppInfo(url=WEBAPP_URL))
        )
    except Exception as e:
        print(f"Could not set menu button: {e}")

if __name__ == "__main__":
    print(f"Bot started. Web App URL: {WEBAPP_URL}")
    bot.infinity_polling()
