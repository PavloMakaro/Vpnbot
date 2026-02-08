import telebot
from telebot import types

# === CONFIGURATION ===
TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY' # From original bot
WEB_APP_URL = 'https://<your-stitch-app-id>.mongodbstitch.com' # REPLACE THIS

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(url=WEB_APP_URL)
    markup.add(types.InlineKeyboardButton("🚀 Open VPN App", web_app=web_app))

    bot.send_message(
        message.chat.id,
        "👋 Welcome to the VPN Bot!\n\n"
        "Click the button below to manage your subscription, balance, and configs.",
        reply_markup=markup
    )

if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True)
