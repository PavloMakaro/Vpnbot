#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import shutil
import zipfile
import datetime
import subprocess
import logging
from pathlib import Path
import telebot
from telebot import types
import threading
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server_backup_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8468632199:AAFieDkPdx7gg4V4ILDKDhTfjkf778BPwZ0"

# Создание экземпляра бота
bot = telebot.TeleBot(BOT_TOKEN)

# Конфигурация по умолчанию
CONFIG = {
    "admin_users": [],  # ID администраторов (будет заполнено автоматически)
    "backup_paths": [
        "/opt/vpn_bot",
        "/opt/vpn_bot/bot.py",
        "/opt/vpn_bot/users.json",
        "/opt/vpn_bot/configs.json", 
        "/opt/vpn_bot/payments.json",
        "/opt/vpn_bot/vpn_bot_env",
        "/etc/systemd/system/vpn_tg_bot.service",
        "/etc/systemd/system/backup_tg_bot.service",
        "/opt/backup_bot",
        "/var/log/syslog",
        "/var/log/auth.log",
        "/home"
    ],
    "max_backup_size": 200 * 1024 * 1024,  # 200MB максимальный размер архива
    "backup_dir": "/tmp/server_backups"
}

# Файл для хранения конфигурации
CONFIG_FILE = "backup_bot_config.json"

def load_config():
    """Загрузка конфигурации из файла"""
    global CONFIG
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                CONFIG.update(saved_config)
    except Exception as e:
        logger.error(f"Ошибка загрузки конфигурации: {e}")

def save_config():
    """Сохранение конфигурации в файл"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения конфигурации: {e}")

def is_admin(user_id):
    """Проверка, является ли пользователь администратором"""
    return user_id in CONFIG["admin_users"]

def add_admin(user_id):
    """Добавление администратора"""
    if user_id not in CONFIG["admin_users"]:
        CONFIG["admin_users"].append(user_id)
        save_config()
        return True
    return False

def get_system_info():
    """Получение информации о системе"""
    try:
        info = {
            "hostname": subprocess.getoutput("hostname"),
            "uptime": subprocess.getoutput("uptime"),
            "disk_usage": subprocess.getoutput("df -h"),
            "memory_usage": subprocess.getoutput("free -h"),
            "cpu_info": subprocess.getoutput("lscpu | head -10"),
            "running_services": subprocess.getoutput("systemctl list-units --type=service --state=running | head -20"),
            "vpn_bot_status": check_vpn_bot_status()
        }
        return info
    except Exception as e:
        logger.error(f"Ошибка получения информации о системе: {e}")
        return {"error": str(e)}

def check_vpn_bot_status():
    """Проверка статуса VPN бота и его файлов"""
    try:
        status_info = {}
        
        # Проверка службы VPN бота
        vpn_service_status = subprocess.getoutput("systemctl is-active vpn_tg_bot.service 2>/dev/null || echo 'inactive'")
        status_info["vpn_service"] = vpn_service_status.strip()
        
        # Проверка файлов VPN бота
        vpn_files = [
            "/opt/vpn_bot/bot.py",
            "/opt/vpn_bot/users.json", 
            "/opt/vpn_bot/configs.json",
            "/opt/vpn_bot/payments.json"
        ]
        
        status_info["vpn_files"] = {}
        for file_path in vpn_files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                status_info["vpn_files"][file_path] = f"✅ {file_size} bytes"
            else:
                status_info["vpn_files"][file_path] = "❌ Не найден"
        
        return status_info
    except Exception as e:
        logger.error(f"Ошибка проверки VPN бота: {e}")
        return {"error": str(e)}

def create_backup(paths, backup_name=None):
    """Создание резервной копии указанных путей"""
    try:
        if not backup_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"server_backup_{timestamp}"
        
        backup_dir = CONFIG["backup_dir"]
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_path = os.path.join(backup_dir, f"{backup_name}.zip")
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            total_size = 0
            
            for path in paths:
                if os.path.exists(path):
                    if os.path.isfile(path):
                        zipf.write(path, os.path.basename(path))
                        total_size += os.path.getsize(path)
                    elif os.path.isdir(path):
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                if os.path.exists(file_path):
                                    arcname = os.path.relpath(file_path, os.path.dirname(path))
                                    zipf.write(file_path, arcname)
                                    total_size += os.path.getsize(file_path)
                                    
                                    # Проверка размера
                                    if total_size > CONFIG["max_backup_size"]:
                                        raise Exception(f"Размер архива превышает лимит {CONFIG['max_backup_size']} байт")
        
        return backup_path, total_size
    except Exception as e:
        logger.error(f"Ошибка создания резервной копии: {e}")
        raise

# Обработчики команд
@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Если это первый пользователь, делаем его администратором
    if not CONFIG["admin_users"]:
        add_admin(user_id)
        bot.reply_to(message, "🎉 Добро пожаловать! Вы назначены администратором бота.")
    
    if is_admin(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📊 Статус сервера", "💾 Создать бэкап")
        markup.row("📁 Список бэкапов", "⚙️ Настройки")
        markup.row("ℹ️ Помощь")
        
        bot.reply_to(message, 
                    "🤖 Бот для резервного копирования сервера запущен!\n\n"
                    "Доступные функции:\n"
                    "📊 Статус сервера - информация о системе\n"
                    "💾 Создать бэкап - создание резервной копии\n"
                    "📁 Список бэкапов - просмотр созданных копий\n"
                    "⚙️ Настройки - управление конфигурацией\n"
                    "ℹ️ Помощь - справка по командам",
                    reply_markup=markup)
    else:
        bot.reply_to(message, "❌ У вас нет прав доступа к этому боту.")

@bot.message_handler(func=lambda message: message.text == "📊 Статус сервера")
def server_status(message):
    """Получение статуса сервера"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Недостаточно прав.")
        return
    
    bot.reply_to(message, "🔄 Получение информации о сервере...")
    
    try:
        info = get_system_info()
        
        if "error" in info:
            bot.reply_to(message, f"❌ Ошибка: {info['error']}")
            return
        
        status_text = f"""
🖥️ **Информация о сервере**

**Хост:** `{info['hostname']}`

**Время работы:**
`{info['uptime']}`

**Использование диска:**
```
{info['disk_usage']}
```

**Использование памяти:**
```
{info['memory_usage']}
```

**Процессор:**
```
{info['cpu_info']}
```

**VPN Бот:**
Служба: `{info['vpn_bot_status'].get('vpn_service', 'неизвестно')}`

**Файлы VPN бота:**
"""
        
        # Добавляем информацию о файлах VPN бота
        if 'vpn_files' in info['vpn_bot_status']:
            for file_path, status in info['vpn_bot_status']['vpn_files'].items():
                file_name = os.path.basename(file_path)
                status_text += f"`{file_name}`: {status}\n"
        
        status_text += f"""
**Запущенные сервисы:**
```
{info['running_services']}
```
        """
        
        bot.reply_to(message, status_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса: {e}")
        bot.reply_to(message, f"❌ Ошибка получения статуса: {e}")

@bot.message_handler(func=lambda message: message.text == "💾 Создать бэкап")
def create_backup_command(message):
    """Создание резервной копии"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Недостаточно прав.")
        return
    
    bot.reply_to(message, "🔄 Создание резервной копии...")
    
    try:
        backup_path, size = create_backup(CONFIG["backup_paths"])
        size_mb = size / (1024 * 1024)
        
        bot.reply_to(message, f"✅ Резервная копия создана!\n"
                             f"📁 Файл: `{os.path.basename(backup_path)}`\n"
                             f"📊 Размер: {size_mb:.2f} MB", parse_mode='Markdown')
        
        # Отправка файла, если он не слишком большой (до 50MB для Telegram)
        if size < 50 * 1024 * 1024:
            with open(backup_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="📦 Резервная копия сервера")
        else:
            bot.reply_to(message, "⚠️ Файл слишком большой для отправки через Telegram.")
            
    except Exception as e:
        logger.error(f"Ошибка создания бэкапа: {e}")
        bot.reply_to(message, f"❌ Ошибка создания бэкапа: {e}")

@bot.message_handler(func=lambda message: message.text == "📁 Список бэкапов")
def list_backups(message):
    """Список созданных резервных копий"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Недостаточно прав.")
        return
    
    try:
        backup_dir = CONFIG["backup_dir"]
        if not os.path.exists(backup_dir):
            bot.reply_to(message, "📁 Папка с резервными копиями пуста.")
            return
        
        backups = []
        for file in os.listdir(backup_dir):
            if file.endswith('.zip'):
                file_path = os.path.join(backup_dir, file)
                size = os.path.getsize(file_path)
                mtime = os.path.getmtime(file_path)
                date = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                backups.append((file, size, date))
        
        if not backups:
            bot.reply_to(message, "📁 Резервные копии не найдены.")
            return
        
        backups.sort(key=lambda x: x[2], reverse=True)  # Сортировка по дате
        
        text = "📁 **Список резервных копий:**\n\n"
        for file, size, date in backups[:10]:  # Показываем последние 10
            size_mb = size / (1024 * 1024)
            text += f"📦 `{file}`\n"
            text += f"📊 Размер: {size_mb:.2f} MB\n"
            text += f"📅 Дата: {date}\n\n"
        
        bot.reply_to(message, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка получения списка бэкапов: {e}")
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def help_command(message):
    """Справка по командам"""
    help_text = """
🤖 **Справка по боту резервного копирования**

**Основные команды:**
📊 Статус сервера - показывает информацию о системе
💾 Создать бэкап - создает резервную копию важных файлов
📁 Список бэкапов - показывает созданные резервные копии
⚙️ Настройки - управление конфигурацией бота

**Что копируется:**
• /opt/vpn_bot - папка с VPN ботом
• /etc/systemd/system/vpn_tg_bot.service - сервис
• /var/log - логи системы
• /home - домашние папки пользователей

**Ограничения:**
• Максимальный размер архива: 100MB
• Отправка через Telegram: до 50MB

**Безопасность:**
• Доступ только для администраторов
• Логирование всех действий
    """
    
    bot.reply_to(message, help_text, parse_mode='Markdown')

def main():
    """Основная функция"""
    logger.info("Запуск бота резервного копирования сервера...")
    
    # Загрузка конфигурации
    load_config()
    
    # Создание папки для бэкапов
    os.makedirs(CONFIG["backup_dir"], exist_ok=True)
    
    logger.info("Бот готов к работе!")
    
    # Запуск бота
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        logger.error(f"Ошибка работы бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
