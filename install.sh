#!/bin/bash

# Проверка, запущен ли скрипт от root
if [ "$(id -u)" != "0" ]; then
    echo "Этот скрипт должен быть запущен с правами root. Используйте sudo."
    exit 1
fi

# Переходим во временную директорию для загрузки и установки
INSTALL_DIR="/opt/vpn_bot"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR" || { echo "Не удалось перейти в директорию $INSTALL_DIR"; exit 1; }

echo "Загрузка файла bot.py из GitHub..."
# Обратите внимание: ai_studio_code.py - это имя, которое вы указали для bot.py
wget -qO bot.py https://raw.githubusercontent.com/PavloMakaro/Vpnbot/main/ai_studio_code.py 

if [ $? -ne 0 ]; then
    echo "Ошибка: Не удалось загрузить bot.py. Проверьте путь и доступность файла."
    exit 1
fi

echo "Обновление списка пакетов..."
apt update -y

echo "Установка python3-full (включает venv)..."
apt install python3-full -y

# Создание и активация виртуального окружения
echo "Создание виртуального окружения..."
python3 -m venv vpn_bot_env

echo "Активация виртуального окружения..."
source vpn_bot_env/bin/activate

# Установка зависимостей
echo "Установка зависимостей (pyTelegramBotAPI)..."
pip install pyTelegramBotAPI

# Создание необходимых JSON файлов, если их нет
echo "Проверка и создание файлов БД..."
for db_file in users.json configs.json payments.json; do
    if [ ! -f "$db_file" ]; then
        echo "{}" > "$db_file"
        echo "Создан пустой файл $db_file"
    fi
done

# Создаем systemd юнит для автозапуска бота
echo "Создание systemd юнита для бота..."
SERVICE_FILE="/etc/systemd/system/vpn_tg_bot.service"

cat << EOF > "$SERVICE_FILE"
[Unit]
Description=VPN Telegram Bot
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/vpn_bot_env/bin/python3 $INSTALL_DIR/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Включение и запуск сервиса
echo "Перезагрузка systemd демона..."
systemctl daemon-reload
echo "Включение сервиса vpn_tg_bot..."
systemctl enable vpn_tg_bot.service
echo "Запуск сервиса vpn_tg_bot..."
systemctl start vpn_tg_bot.service

echo "Бот успешно установлен и запущен как systemd сервис."
echo "Статус бота можно проверить командой: systemctl status vpn_tg_bot.service"
echo "Логи бота можно посмотреть командой: journalctl -u vpn_tg_bot.service -f"
echo "Бот будет автоматически запускаться после перезагрузки сервера."

# Деактивация виртуального окружения
deactivate
