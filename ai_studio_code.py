import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Токен бота
BOT_TOKEN = "8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY"

# Создаем экземпляр бота
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    # Создаем клавиатуру с кнопкой
    keyboard = InlineKeyboardMarkup()
    support_button = InlineKeyboardButton("Поддержка", url="https://t.me/Gl1ch555")
    keyboard.add(support_button)
    
    # Отправляем сообщение с кнопкой
    bot.send_message(
        message.chat.id,
        "Бот находится на тех обслуживании. По вопросам обращайтесь в поддержку.",
        reply_markup=keyboard
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Обработчик всех остальных сообщений"""
    # Создаем клавиатуру с кнопкой
    keyboard = InlineKeyboardMarkup()
    support_button = InlineKeyboardButton("Поддержка", url="https://t.me/Gl1ch555")
    keyboard.add(support_button)
    
    # Отправляем сообщение с кнопкой
    bot.send_message(
        message.chat.id,
        "Бот находится на тех обслуживании. По вопросам обращайтесь в поддержку.",
        reply_markup=keyboard
    )

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
