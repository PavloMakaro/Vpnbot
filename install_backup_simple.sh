#!/bin/bash

# Проверка, запущен ли скрипт от root
if [ "$(id -u)" != "0" ]; then
    echo "Этот скрипт должен быть запущен с правами root. Используйте sudo."
    exit 1
fi

# Переходим во временную директорию для загрузки и установки
INSTALL_DIR="/opt/backup_bot"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR" || { echo "Не удалось перейти в директорию $INSTALL_DIR"; exit 1; }

# Остановка старого бота, если он запущен
echo "Проверка запущенного бота резервного копирования..."
if systemctl is-active --quiet backup_tg_bot.service; then
    echo "Останавливаю работающий бот..."
    systemctl stop backup_tg_bot.service
    sleep 3
    echo "Старый бот остановлен."
else
    echo "Бот не запущен, продолжаем установку..."
fi

echo "Загрузка файла bot.py из GitHub..."
wget -qO bot.py https://raw.githubusercontent.com/PavloMakaro/Vpnbot/main/server_backup_bot.py 

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
python3 -m venv backup_bot_env

echo "Активация виртуального окружения..."
source backup_bot_env/bin/activate

# Установка зависимостей
echo "Установка зависимостей..."
pip install pyTelegramBotAPI
pip install requests
pip install pathlib2

# Создание необходимых директорий и файлов
echo "Создание директорий и конфигурации..."
mkdir -p /tmp/server_backups
chmod 755 /tmp/server_backups

# Создание файла конфигурации, если его нет
if [ ! -f "backup_bot_config.json" ]; then
    cat << 'EOF' > backup_bot_config.json
{
    "admin_users": [],
    "backup_paths": [
        "/opt/vpn_bot",
        "/etc/systemd/system/vpn_tg_bot.service",
        "/var/log",
        "/home"
    ],
    "max_backup_size": 104857600,
    "backup_dir": "/tmp/server_backups"
}
EOF
    echo "Создан файл конфигурации backup_bot_config.json"
fi

# Создаем systemd юнит для автозапуска бота
echo "Создание systemd юнита для бота резервного копирования..."
SERVICE_FILE="/etc/systemd/system/backup_tg_bot.service"

cat << EOF > "$SERVICE_FILE"
[Unit]
Description=Telegram Server Backup Bot
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/backup_bot_env/bin/python3 $INSTALL_DIR/bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Включение и запуск сервиса
echo "Перезагрузка systemd демона..."
systemctl daemon-reload
echo "Включение сервиса backup_tg_bot..."
systemctl enable backup_tg_bot.service

echo "Запуск нового бота резервного копирования..."
systemctl start backup_tg_bot.service

# Проверка статуса
sleep 2
if systemctl is-active --quiet backup_tg_bot.service; then
    echo "✅ Новый бот резервного копирования успешно запущен!"
else
    echo "⚠️  Бот не запустился автоматически. Проверьте логи: journalctl -u backup_tg_bot.service -f"
fi

echo ""
echo "Бот резервного копирования успешно установлен как systemd сервис."
echo ""
echo "ВАЖНО! Настройте бота:"
echo "1. Отредактируйте файл: $INSTALL_DIR/backup_bot_config.json"
echo "2. Добавьте ваш Telegram Bot Token"
echo "3. Добавьте ваш Telegram User ID в admin_users"
echo "4. Перезапустите бота: systemctl restart backup_tg_bot.service"
echo ""
echo "Управление ботом:"
echo "Статус бота: systemctl status backup_tg_bot.service"
echo "Логи бота: journalctl -u backup_tg_bot.service -f"
echo "Остановить бота: systemctl stop backup_tg_bot.service"
echo "Перезапустить бота: systemctl restart backup_tg_bot.service"
echo "Бот будет автоматически запускаться после перезагрузки сервера."

# Деактивация виртуального окружения
deactivate