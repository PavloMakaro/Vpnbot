#!/bin/bash

# Скрипт для автоматической установки и запуска Telegram VPN бота на Ubuntu 24.04

# --- 1. Обновление системы и установка зависимостей ---
echo "--- Обновление системы и установка необходимых пакетов ---"
sudo apt update
sudo apt install -y python3 python3-pip git screen # Добавляем screen для возможности ручного запуска в сессии

# --- 2. Клонирование репозитория (если его еще нет) ---
echo "--- Клонирование репозитория с GitHub ---"
BOT_DIR="/opt/vpn_bot" # Директория для бота
REPO_URL="https://github.com/PavloMakaro/Vpnbot"
SCRIPT_NAME="ai_studio_code.py" # Имя вашего файла бота

if [ ! -d "$BOT_DIR" ]; then
    sudo git clone "$REPO_URL" "$BOT_DIR"
    echo "Репозиторий клонирован в $BOT_DIR"
else
    echo "Директория $BOT_DIR уже существует. Обновляем код..."
    sudo git -C "$BOT_DIR" pull
    echo "Код обновлен."
fi

# --- 3. Переход в директорию бота и установка зависимостей в виртуальное окружение ---
echo "--- Установка зависимостей в виртуальное окружение ---"
cd "$BOT_DIR" || { echo "Не удалось перейти в директорию бота. Выход."; exit 1; }

# Создаем виртуальное окружение, если его нет
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Виртуальное окружение 'venv' создано."
fi

# Активируем виртуальное окружение и устанавливаем aiogram
source venv/bin/activate
pip install aiogram
deactivate # Деактивируем после установки

echo "Зависимости установлены."

# --- 4. Создание папки для конфигов, если ее нет ---
echo "--- Создание папки 'configs' ---"
if [ ! -d "configs" ]; then
    mkdir configs
    echo "Папка 'configs' создана. Пожалуйста, вручную загрузите ваши VPN-конфиги в $BOT_DIR/configs"
else
    echo "Папка 'configs' уже существует."
fi

# --- 5. Настройка Systemd сервиса для запуска бота в фоне ---
echo "--- Настройка Systemd сервиса ---"
SERVICE_FILE="/etc/systemd/system/vpn_bot.service"
USERNAME=$(whoami) # Получаем текущего пользователя (root в вашем случае)

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Telegram VPN Bot
After=network.target

[Service]
User=$USERNAME
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python $SCRIPT_NAME # Запускаем через Python из виртуального окружения
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

echo "Файл сервиса Systemd создан: $SERVICE_FILE"

# --- 6. Запуск и активация Systemd сервиса ---
echo "--- Запуск и активация Systemd сервиса ---"
sudo systemctl daemon-reload
sudo systemctl enable vpn_bot
sudo systemctl start vpn_bot

echo "--- Проверка статуса бота ---"
sudo systemctl status vpn_bot

echo "--- Установка завершена! ---"
echo "Бот должен быть запущен в фоновом режиме."
echo "Не забудьте загрузить ваши VPN-конфиги в папку '$BOT_DIR/configs'!"
echo "Для просмотра логов бота: sudo journalctl -u vpn_bot -f"
echo "Для обновления бота (после изменений на GitHub):"
echo "  cd $BOT_DIR"
echo "  sudo git pull"
echo "  sudo systemctl restart vpn_bot"
echo ""
echo "--- Рекомендуется сменить пароль root: 'passwd' ---"
