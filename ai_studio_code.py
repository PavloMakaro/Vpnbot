import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота
BOT_TOKEN = "8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    # Создаем кнопку "Поддержка"
    keyboard = [
        [InlineKeyboardButton("Поддержка", url="https://t.me/Gl1ch555")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение с кнопкой
    await update.message.reply_text(
        "Бот находится на тех обслуживании. По вопросам обращайтесь в поддержку.",
        reply_markup=reply_markup
    )

def main():
    """Основная функция запуска бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчик команды /start
    application.add_handler(CommandHandler("start", start))
    
    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
