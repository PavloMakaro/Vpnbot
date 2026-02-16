import telebot
from telebot import types
import os

# CONFIGURATION
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://<your-app-id>.mongodbstitch.com/")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Открыть VPN App", web_app=types.WebAppInfo(url=WEB_APP_URL)))

    bot.send_message(message.chat.id,
                     "👋 **Добро пожаловать!**\n\n"
                     "Управляйте подпиской и конфигами через наше удобное мини-приложение.",
                     parse_mode='Markdown',
                     reply_markup=markup)

if __name__ == "__main__":
    print("Bot started...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Error: {e}")
