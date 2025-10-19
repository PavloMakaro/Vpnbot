#!/bin/bash

# --- КОНФИГУРАЦИЯ ---
REPO_URL="https://github.com/PavloMakaro/Vpnbot.git"
BOT_DIR="/opt/vpn_bot"
BOT_SERVICE_NAME="vpn_bot"
BOT_SCRIPT_NAME="ai_studio_code.py"
VM_USER="root" # Имя пользователя, под которым запускается VM (root в вашем случае)
PYTHON_EXECUTABLE="python3"

# --- СООБЩЕНИЯ ---
echo "--- Запуск автоматической установки VPN Telegram Bot ---"

# --- ШАГ 1: Обновление системы и установка необходимых пакетов ---
echo "Обновление списка пакетов и установка Git, Python3, pip..."
sudo apt update -y
sudo apt install git "$PYTHON_EXECUTABLE" "$PYTHON_EXECUTABLE"-venv "$PYTHON_EXECUTABLE"-pip -y || { echo "Ошибка установки системных пакетов. Выход."; exit 1; }

# --- ШАГ 2: Клонирование репозитория в указанную директорию ---
echo "Клонирование репозитория $REPO_URL в $BOT_DIR..."
if [ -d "$BOT_DIR" ]; then
    echo "Директория $BOT_DIR уже существует. Удаляем ее для чистой установки..."
    sudo rm -rf "$BOT_DIR" || { echo "Ошибка удаления старой директории. Выход."; exit 1; }
fi
sudo git clone "$REPO_URL" "$BOT_DIR" || { echo "Ошибка клонирования репозитория. Выход."; exit 1; }
echo "Репозиторий успешно клонирован."

# --- ШАГ 3: Создание и активация виртуального окружения ---
echo "Создание виртуального окружения..."
sudo "$PYTHON_EXECUTABLE" -m venv "$BOT_DIR/venv" || { echo "Ошибка создания виртуального окружения. Выход."; exit 1; }

# --- ШАГ 4: Установка зависимостей в виртуальное окружение ---
echo "Установка зависимостей Python (aiogram)..."
sudo "$BOT_DIR/venv/bin/pip" install aiogram || { echo "Ошибка установки aiogram. Выход."; exit 1; }

# --- ШАГ 5: Создание папки для конфигов VPN ---
echo "Создание папки для конфигов VPN: $BOT_DIR/configs"
sudo mkdir -p "$BOT_DIR/configs" || { echo "Ошибка создания папки configs. Выход."; exit 1; }
echo "ПАПКА ДЛЯ КОНФИГОВ СОЗДАНА. НЕ ЗАБУДЬТЕ ВРУЧНУЮ ЗАГРУЗИТЬ В НЕЕ ВАШИ .conf ФАЙЛЫ!"

# --- ШАГ 6: Создание Systemd сервиса ---
echo "Создание Systemd сервиса для бота..."
SERVICE_FILE="/etc/systemd/system/$BOT_SERVICE_NAME.service"
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Telegram VPN Bot
After=network.target

[Service]
User=$VM_USER
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/$PYTHON_EXECUTABLE $BOT_SCRIPT_NAME
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# --- ШАГ 7: Перезагрузка Systemd, включение и запуск сервиса ---
echo "Перезагрузка Systemd, включение и запуск сервиса..."
sudo systemctl daemon-reload || { echo "Ошибка daemon-reload. Выход."; exit 1; }
sudo systemctl enable "$BOT_SERVICE_NAME" || { echo "Ошибка enable сервиса. Выход."; exit 1; }
sudo systemctl start "$BOT_SERVICE_NAME" || { echo "Ошибка запуска сервиса. Выход."; exit 1; }

echo "--- Установка завершена! ---"
echo "Бот запущен. Проверьте его статус командой: sudo systemctl status $BOT_SERVICE_NAME"
echo "Для просмотра логов: sudo journalctl -u $BOT_SERVICE_NAME -f"
echo "НЕ ЗАБУДЬТЕ ЗАГРУЗИТЬ ВАШИ VPN-КОНФИГИ В ДИРЕКТОРИЮ $BOT_DIR/configs НА VM!"
echo "После загрузки конфигов перезапустите бота: sudo systemctl restart $BOT_SERVICE_NAME"
