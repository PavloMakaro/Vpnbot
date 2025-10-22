import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен вашего бота
BOT_TOKEN = "8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY"

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    # Создаем кнопку "Поддержка"
    keyboard = [
        [InlineKeyboardButton("Поддержка Gl1ch555", url="https://t.me/Gl1ch555")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Текст сообщения
    message_text = (
        "🤖 Бот находится на тех обслуживании\n\n"
        "По вопросам обращайтесь в поддержку"
    )
    
    # Отправляем сообщение с кнопкой
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup
    )

def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчик команды /start
    application.add_handler(CommandHandler("start", start))
    
    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
