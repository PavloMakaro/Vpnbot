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

# Остановка старого бота, если он запущен
echo "Проверка запущенного бота..."
if systemctl is-active --quiet vpn_tg_bot.service; then
    echo "Останавливаю работающий бот..."
    systemctl stop vpn_tg_bot.service
    sleep 3
    echo "Старый бот остановлен."
else
    echo "Бот не запущен, продолжаем установку..."
fi

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
pip install yookassa
pip3 install python-telegram-bot
# Activate your virtual environment if you're using one
# source /path/to/your/venv/bin/activate

# Install yookassa package
pip3 install yookassa
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
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Включение и запуск сервиса
echo "Перезагрузка systemd демона..."
systemctl daemon-reload
echo "Включение сервиса vpn_tg_bot..."
systemctl enable vpn_tg_bot.service

echo "Запуск нового бота..."
systemctl start vpn_tg_bot.service

# Проверка статуса
sleep 2
if systemctl is-active --quiet vpn_tg_bot.service; then
    echo "✅ Новый бот успешно запущен!"
else
    echo "⚠️  Бот не запустился автоматически. Проверьте логи: journalctl -u vpn_tg_bot.service -f"
fi

echo ""
echo "Бот успешно установлен/обновлен как systemd сервис."
echo "Статус бота можно проверить командой: systemctl status vpn_tg_bot.service"
echo "Логи бота можно посмотреть командой: journalctl -u vpn_tg_bot.service -f"
echo "Остановить бота: systemctl stop vpn_tg_bot.service"
echo "Перезапустить бота: systemctl restart vpn_tg_bot.service"
echo "Бот будет автоматически запускаться после перезагрузки сервера."

# Деактивация виртуального окружения
deactivate
