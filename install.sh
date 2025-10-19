#!/bin/bash

# Обновление списка пакетов
echo "Обновление списка пакетов..."
sudo apt update -y

# Установка python3-full (включает venv)
echo "Установка python3-full..."
sudo apt install python3-full -y

# Создание и активация виртуального окружения
echo "Создание виртуального окружения..."
python3 -m venv vpn_bot_env

echo "Активация виртуального окружения..."
source vpn_bot_env/bin/activate

# Установка зависимостей
echo "Установка зависимостей..."
pip install pyTelegramBotAPI # Используем pyTelegramBotAPI, так как вы упомянули telebot

# Создание необходимых JSON файлов, если их нет
echo "Проверка и создание файлов БД..."
touch users.json
if [ ! -s users.json ]; then
  echo "{}" > users.json
fi

touch configs.json
if [ ! -s configs.json ]; then
  echo "{}" > configs.json
fi

touch payments.json
if [ ! -s payments.json ]; then
  echo "{}" > payments.json
fi


# Запуск бота в фоновом режиме с редиректом вывода в лог файл
echo "Запуск бота в фоновом режиме..."
nohup python3 bot.py > bot_output.log 2>&1 &

echo "Бот успешно установлен и запущен в фоновом режиме."
echo "Вывод бота можно посмотреть в файле bot_output.log"
echo "Для остановки бота найдите его процесс (например, 'ps aux | grep bot.py') и используйте 'kill <PID>'."
echo "Для повторной активации окружения и запуска: 'cd /path/to/your/bot/directory && source vpn_bot_env/bin/activate && python3 bot.py'"
