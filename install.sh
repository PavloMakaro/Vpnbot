#!/bin/bash

# Название файла бота
BOT_FILE="vpnbot.py"

# Проверка и установка python3-full (для venv)
echo "Проверка и установка python3-full..."
sudo apt update
sudo apt install -y python3-full screen

# Создание виртуального окружения (venv)
echo "Создание виртуального окружения..."
python3 -m venv venv

# Активация venv
source venv/bin/activate

# Установка aiogram в venv
echo "Установка необходимых библиотек (aiogram)..."
pip install aiogram

# Деактивация venv
deactivate

# Проверка наличия файла бота (должен быть в той же директории)
if [ ! -f "$BOT_FILE" ]; then
    echo "❌ Ошибка: Файл бота $BOT_FILE не найден в текущей директории."
    exit 1
fi

# Запуск бота в screen
# -S vpn_bot: Имя сессии screen
# venv/bin/python3 $BOT_FILE: Команда запуска бота через python из venv
echo "Запуск Telegram-бота ($BOT_FILE) в фоновом режиме (screen)..."
screen -dmS vpn_bot bash -c "source venv/bin/activate; venv/bin/python3 $BOT_FILE"

echo "✅ Бот успешно запущен в фоновом режиме!"
echo "--------------------------------------------------------"
echo "Для проверки статуса бота:"
echo "screen -r vpn_bot"
echo "Для выхода из screen без остановки бота: нажмите Ctrl+A, затем D"
echo "Для остановки бота: войдите в screen и нажмите Ctrl+C"

exit 0
