#!/bin/bash

# Имя директории для бота на сервере
BOT_DIR="vpn_bot"
# Имя вашего Python скрипта
BOT_SCRIPT="ai_studio_code.py"
# URL вашего GitHub репозитория
REPO_URL="https://github.com/PavloMakaro/Vpnbot.git"
# Пользователь, под которым будет запущен сервис (root в вашем случае)
SERVICE_USER="root"
# Путь к домашней директории пользователя
USER_HOME="/root"

echo "Начинаем установку Telegram VPN бота..."

# 1. Обновление пакетов и установка необходимых утилит
echo "Обновляем системные пакеты и устанавливаем Python, pip, git..."
sudo apt update -y
sudo apt install python3 python3-pip git python3.12-venv -y # python3.12-venv для создания venv
echo "Системные пакеты установлены."

# 2. Переходим в домашнюю директорию и клонируем репозиторий
cd "${USER_HOME}" || { echo "Не удалось перейти в ${USER_HOME}. Выход."; exit 1; }

if [ -d "${BOT_DIR}" ]; then
    echo "Директория ${BOT_DIR} уже существует. Удаляем и клонируем заново."
    rm -rf "${BOT_DIR}"
fi

echo "Клонируем репозиторий ${REPO_URL} в ${BOT_DIR}..."
git clone "${REPO_URL}" "${BOT_DIR}" || { echo "Не удалось клонировать репозиторий. Проверьте URL и доступ. Выход."; exit 1; }
cd "${BOT_DIR}" || { echo "Не удалось перейти в директорию ${BOT_DIR}. Выход."; exit 1; }
echo "Репозиторий успешно клонирован."

# 3. Создаем виртуальное окружение и устанавливаем зависимости
echo "Создаем и активируем виртуальное окружение..."
python3 -m venv venv || { echo "Не удалось создать виртуальное окружение. Убедитесь, что python3.12-venv установлен. Выход."; exit 1; }
source venv/bin/activate
echo "Виртуальное окружение активировано."

echo "Устанавливаем aiogram в виртуальное окружение..."
pip install aiogram || { echo "Не удалось установить aiogram. Выход."; exit 1; }
echo "aiogram успешно установлен."
deactivate # Деактивируем venv после установки

# 4. Создаем systemd сервис для фонового запуска
echo "Создаем systemd сервис для бота..."
SERVICE_FILE="/etc/systemd/system/${BOT_DIR}.service"

cat <<EOF | sudo tee "${SERVICE_FILE}" > /dev/null
[Unit]
Description=Telegram VPN Bot
After=network.target

[Service]
User=${SERVICE_USER}
WorkingDirectory=${USER_HOME}/${BOT_DIR}
ExecStart=${USER_HOME}/${BOT_DIR}/venv/bin/python ${BOT_SCRIPT}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Сервис ${BOT_DIR}.service создан."

# 5. Запускаем сервис
echo "Перезагружаем systemd, включаем и запускаем сервис бота..."
sudo systemctl daemon-reload
sudo systemctl enable "${BOT_DIR}"
sudo systemctl start "${BOT_DIR}"

echo "Проверяем статус сервиса..."
sudo systemctl status "${BOT_DIR}"

echo "Установка завершена! Бот должен быть запущен."
echo "Вы можете проверить логи бота командой: sudo journalctl -u ${BOT_DIR} -f"
echo "Если хотите остановить бота: sudo systemctl stop ${BOT_DIR}"
echo "Если хотите перезапустить бота: sudo systemctl restart ${BOT_DIR}"
echo "Теперь вы можете добавить VPN-конфиги через админ-панель бота, используя команду /admin!"
