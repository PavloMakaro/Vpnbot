import telebot
from telebot import types
import json
import os

# === CONFIGURATION ===
# Replace with your actual token
TOKEN = os.getenv('BOT_TOKEN', 'YOUR_TOKEN_HERE')
ADMIN_ID = int(os.getenv('ADMIN_ID', '8320218178'))
# URL to your hosted Mini App (e.g. GitHub Pages or Stitch Hosting)
# For testing, you can use a placeholder or local tunnel
WEB_APP_URL = "https://your-mini-app-url.com"

bot = telebot.TeleBot(TOKEN)

# === COMMANDS ===

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    # Create the inline keyboard with the Mini App button
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(url=WEB_APP_URL)
    markup.add(types.InlineKeyboardButton("🚀 Open VPN App", web_app=web_app))

    # Also add a support button
    markup.add(types.InlineKeyboardButton("👨‍💻 Support", url="https://t.me/Gl1ch555"))

    welcome_text = (
        f"👋 **Hello, {first_name}!**\n\n"
        f"Welcome to the VPN Bot Mini App.\n"
        f"Manage your subscriptions, top up balance, and get configs directly in our new app!\n\n"
        f"👇 Click the button below to start."
    )

    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=markup)

    # Set the Menu Button (The blue button next to text input)
    try:
        bot.set_chat_menu_button(
            message.chat.id,
            types.MenuButtonWebApp(type="web_app", text="Open App", web_app=types.WebAppInfo(url=WEB_APP_URL))
        )
    except Exception as e:
        print(f"Error setting menu button: {e}")

@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    # Handle data sent back from the Web App (if any)
    try:
        data = json.loads(message.web_app_data.data)
        bot.send_message(message.chat.id, f"Received data: {data}")
    except Exception as e:
        print(e)

# === ADMIN COMMANDS ===
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "Admin panel is now part of the database management system (Stitch).")

print("Bot is running...")
bot.infinity_polling()
