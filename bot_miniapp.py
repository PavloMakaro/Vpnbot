import telebot
from telebot import types
import os

# === CONFIGURATION ===
# Replace with your actual token or use environment variable
TOKEN = os.environ.get('BOT_TOKEN', '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY')
# Replace with your deployed Mini App URL (e.g., from Firebase Hosting, GitHub Pages, or MongoDB App Services Hosting)
MINI_APP_URL = os.environ.get('MINI_APP_URL', 'https://<your-app-id>.mongodbstitch.com')

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(MINI_APP_URL)
    markup.add(types.InlineKeyboardButton("🚀 Open VPN App", web_app=web_app))

    bot.send_message(
        message.chat.id,
        f"👋 **Welcome, {first_name}!**\n\n"
        f"Manage your VPN subscription, top up balance, and get configs directly in our new Mini App.\n\n"
        f"Click the button below to start!",
        parse_mode='Markdown',
        reply_markup=markup
    )

    # Set the Menu Button to open the Web App directly (optional but recommended)
    try:
        bot.set_chat_menu_button(
            message.chat.id,
            types.MenuButtonWebApp("VPN App", types.WebAppInfo(MINI_APP_URL))
        )
    except Exception as e:
        print(f"Failed to set menu button: {e}")

@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    # Handle data sent back from the Web App if needed
    print(f"Received data: {message.web_app_data.data}")

if __name__ == "__main__":
    print(f"Bot started. Mini App URL: {MINI_APP_URL}")
    bot.infinity_polling()
