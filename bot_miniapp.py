import telebot
from telebot.types import MenuButtonWebApp, WebAppInfo
import os

# Use environment variable.
# Make sure to set BOT_TOKEN when running this script.
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("Error: BOT_TOKEN environment variable not set.")
    exit(1)

bot = telebot.TeleBot(TOKEN)

# REPLACE THIS WITH YOUR DEPLOYED MINI APP URL (e.g., Firebase Hosting or GitHub Pages or Stitch Hosting)
WEB_APP_URL = os.environ.get('WEB_APP_URL', "https://example.com/vpn-mini-app")

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Open VPN App 🚀", web_app=WebAppInfo(url=WEB_APP_URL)))

    bot.send_message(message.chat.id,
                     "Welcome to VPN Bot! \n\nManage your subscription, top up balance, and get configs directly in our Mini App.",
                     reply_markup=markup)

    try:
        # Set the menu button for this user
        bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(type="web_app", text="Open App", web_app=WebAppInfo(url=WEB_APP_URL))
        )
    except Exception as e:
        print(f"Error setting menu button: {e}")

if __name__ == '__main__':
    print(f"Bot started with Web App URL: {WEB_APP_URL}")
    bot.infinity_polling()
