#!/bin/bash

# --- КОНФИГУРАЦИЯ ---
# Базовая ссылка на репозиторий
REPO_BASE_URL="https://raw.githubusercontent.com/PavloMakaro/Vpnbot/main"
# Имя файла бота в вашем репозитории
BOT_FILE="ai_studio_code.py" 
# Директория для установки (будет удалена и создана заново при каждом запуске)
INSTALL_DIR="/root/vpnbot_data"
# Имя сессии screen
SCREEN_NAME="vpn_bot"

echo "=================================================="
echo "🚀 VPN Telegram Bot: Скрипт автоматической установки"
echo "=================================================="

# 1. Проверка системных пакетов и установка
echo "Обновление списка пакетов и установка git, screen, wget, python3-full..."
# Устанавливаем необходимые пакеты
sudo apt update
sudo apt install -y python3-full python3-venv git screen wget

# 2. Создание директории и переход в нее
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️ Директория $INSTALL_DIR существует. Удаляем для чистой установки..."
    rm -rf "$INSTALL_DIR"
fi

echo "Создание новой директории $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR" || { echo "❌ Ошибка: Не удалось перейти в директорию $INSTALL_DIR. Выход."; exit 1; }

# 3. Загрузка файла бота
echo "Загрузка файла бота ($BOT_FILE) из GitHub..."
wget -O "$BOT_FILE" "$REPO_BASE_URL/$BOT_FILE"

if [ $? -ne 0 ]; then
    echo "❌ Ошибка: Не удалось загрузить файл бота. Проверьте имя файла ($BOT_FILE) в репозитории."
    exit 1
fi

# 4. Создание и активация виртуального окружения (venv)
echo "Создание виртуального окружения..."
python3 -m venv venv

# Установка aiogram
echo "Установка совместимой версии aiogram (V2.*) в venv..."
source venv/bin/activate
# !!! ИСПРАВЛЕНИЕ: Установка aiogram V2 для поддержки 'executor' !!!
pip install aiogram==2.*

if [ $? -ne 0 ]; then
    echo "❌ Ошибка: Не удалось установить aiogram. Проверьте права доступа."
    deactivate
    exit 1
fi

# 5. Запуск бота в screen
echo "Запуск Telegram-бота ($BOT_FILE) в фоновом режиме (screen: $SCREEN_NAME)..."

# Проверка, не запущен ли уже screen с таким именем, и остановка старой сессии
screen -ls | grep -q "$SCREEN_NAME"
if [ $? -eq 0 ]; then
    echo "ℹ️ Сессия screen '$SCREEN_NAME' уже запущена. Останавливаем старую..."
    # Отправка команды "quit" в старую сессию screen
    screen -X -S "$SCREEN_NAME" quit
fi

# Запуск бота: активируем venv, запускаем python3, и все это в screen
screen -dmS "$SCREEN_NAME" bash -c "source $INSTALL_DIR/venv/bin/activate && python3 $BOT_FILE"

echo "=================================================="
echo "✅ Бот успешно установлен и запущен в фоновом режиме!"
echo "   Директория установки: $INSTALL_DIR"
echo "--------------------------------------------------"
echo "💻 Команды для управления ботом:"
echo "1. Зайти в консоль бота (проверить логи): screen -r $SCREEN_NAME"
echo "2. Выйти из screen (не останавливая бота): Нажмите Ctrl+A, затем D"
echo "=================================================="

exit 0
