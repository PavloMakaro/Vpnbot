import telebot
from telebot.types import MenuButtonWebApp, WebAppInfo
import os

# Configuration
TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY' # Replace with your bot token if different
MINI_APP_URL = "https://your-app-id.mongodbstitch.com/" # REPLACE THIS with your hosted Mini App URL

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    """
    Handle /start command.
    Sends a welcome message with a button to open the Mini App.
    """
    user_name = message.from_user.first_name

    # Create Inline Keyboard with Web App button
    markup = telebot.types.InlineKeyboardMarkup()
    web_app_info = WebAppInfo(url=MINI_APP_URL)
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open VPN App", web_app=web_app_info))

    welcome_text = (
        f"👋 Hello, {user_name}!\n\n"
        "Manage your VPN subscription, top up balance, and get configs easily "
        "using our new Mini App.\n\n"
        "Click the button below to start!"
    )

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

    # Set the persistent Menu Button to open the Web App
    try:
        bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(type="web_app", text="Open App", web_app=web_app_info)
        )
    except Exception as e:
        print(f"Failed to set menu button: {e}")

@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    """
    Handle data sent from the Mini App (if any).
    """
    print(f"Received data from Web App: {message.web_app_data.data}")
    # You can process data here if your Mini App sends data back to the bot via sendData()

if __name__ == "__main__":
    print("Bot is running...")
    # Verify token
    try:
        bot_info = bot.get_me()
        print(f"Logged in as @{bot_info.username}")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Error starting bot: {e}")
