# -*- coding: utf-8 -*-
import telebot
from telebot import types
import json
import time
import datetime
import threading
import os
import subprocess
import signal
import sys

TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY'
ADMIN_USERNAME = '@Gl1ch555'
ADMIN_ID = 8320218178  # Пожалуйста, измените этот ID на ваш фактический ID администратора!
CARD_NUMBER = '2204320690808227'
CARD_HOLDER = 'Makarov Pavel Alexandrovich (Ozon Bank)'

# Определение цен и периодов подписки
SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
}

# Примерные константы, которые могут быть определены в другом месте
PRICE_MONTH = SUBSCRIPTION_PERIODS['1_month']['price']
PRICE_2_MONTHS = SUBSCRIPTION_PERIODS['2_months']['price']
PRICE_3_MONTHS = SUBSCRIPTION_PERIODS['3_months']['price']
STARS_TO_RUB = 1 # Примерное соотношение, уточните реальное
REFERRAL_BONUS_NEW_USER = 50
REFERRAL_BONUS_REFERRER = 25
MAINTENANCE_MODE = False # Пример, определите в вашем коде

# --- Функции для работы с JSON ---
def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- Загрузка баз данных ---
users_db = load_data('users.json')
configs_db = load_data('configs.json')
payments_db = load_data('payments.json')

# Сброс всех конфигов при запуске для новой инициализации по запросу
# Если вы не хотите сбрасывать конфиги при каждом запуске, закомментируйте эти строки
configs_db = {
    '1_month': [],
    '2_months': [],
    '3_months': []
}

# --- Определение функций, используемых в обработчиках ---

def get_subscription_days_left(user_id):
    user_info = users_db.get(str(user_id), {})
    subscription_end = user_info.get('subscription_end')
    if subscription_end:
        try:
            end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
            now = datetime.datetime.now()
            if end_date > now:
                return (end_date - now).days
            else:
                return 0
        except ValueError:
            return 0
    return 0

def main_menu_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    # Пример кнопок
    # markup.add(types.InlineKeyboardButton("Профиль", callback_data="my_account"))
    # markup.add(types.InlineKeyboardButton("Купить VPN", callback_data="buy_vpn"))
    # markup.add(types.InlineKeyboardButton("Реферальная программа", callback_data="referral_program"))
    # markup.add(types.InlineKeyboardButton("Поддержка", url=ADMIN_USERNAME))
    return markup

def buy_vpn_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"1 месяц ({PRICE_MONTH} ₽)", callback_data="choose_period_1_month"),
        types.InlineKeyboardButton(f"2 месяца ({PRICE_2_MONTHS} ₽)", callback_data="choose_period_2_months"),
        types.InlineKeyboardButton(f"3 месяца ({PRICE_3_MONTHS} ₽)", callback_data="choose_period_3_months"),
        types.InlineKeyboardButton("Назад", callback_data="main_menu")
    )
    return markup

def payment_methods_keyboard(period_callback_data, amount, user_balance):
    stars_amount = int(amount / STARS_TO_RUB)
    markup = types.InlineKeyboardMarkup(row_width=1)
    needed_amount = max(0, amount - user_balance)

    if needed_amount == 0:
        # Вся сумма покрывается балансом
        markup.add(
            types.InlineKeyboardButton(f"💳 Оплата с баланса ({amount} ₽)", callback_data=f"pay_balance_{period_callback_data}")
        )
    else:
        # Требуется частичная оплата или оплата картой
        if user_balance > 0:
            # Сначала списать с баланса, потом картой
            markup.add(
                types.InlineKeyboardButton(f"💳 Оплата с баланса + карта ({user_balance} ₽ + {needed_amount} ₽)", callback_data=f"pay_balance_partial_{period_callback_data}_{amount}")
            )
        # Оплата картой
        markup.add(
            types.InlineKeyboardButton(f"💳 Оплата картой ({amount} ₽)", callback_data=f"pay_card_{period_callback_data}_{amount}"),
            types.InlineKeyboardButton(f"🪙 Оплата Stars ({stars_amount} XTR)", callback_data=f"pay_stars_{period_callback_data}_{amount}")
        )
    markup.add(
        types.InlineKeyboardButton("Назад", callback_data="buy_vpn")
    )
    return markup

def my_configs_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    # Проверяем, есть ли активная подписка
    days_left = get_subscription_days_left(user_id)
    if days_left > 0:
        # Если есть активная подписка, показываем кнопки для получения конфигов
        for period_key in SUBSCRIPTION_PERIODS.keys():
            display_period = SUBSCRIPTION_PERIODS[period_key]['days']
            markup.add(
                types.InlineKeyboardButton(f"Конфиг на {display_period} дней", callback_data=f"get_config_{period_key}")
            )
    else:
        # Если подписка не активна
        markup.add(
            types.InlineKeyboardButton("❌ Подписка не активна", callback_data="noop")
        )
    markup.add(
        types.InlineKeyboardButton("Назад", callback_data="my_account")
    )
    return markup

def get_available_config(period):
    # Пример функции, возвращает первый доступный конфиг для периода
    # Реализация зависит от структуры configs_db
    configs = configs_db.get(period, [])
    for config in configs:
        if not config.get('used', False): # Предполагается поле 'used'
            return config
    return None

def mark_config_used(period, config_link):
    # Пример функции, отмечает конфиг как использованный
    # Реализация зависит от структуры configs_db
    for config in configs_db.get(period, []):
        if config.get('link') == config_link:
            config['used'] = True
            save_data('configs.json', configs_db) # Сохраняем сразу
            return True
    return False

def send_config_to_user(user_id, period, username, first_name):
    config = get_available_config(period)
    if not config:
        return False, "Нет доступных конфигов для этого периода"

    mark_config_used(period, config['link'])
    config_name = f"{first_name} ({username}) - {period.replace('_', ' ')}"
    issue_date = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

    if 'used_configs' not in users_db[str(user_id)]:
        users_db[str(user_id)]['used_configs'] = []

    used_config = {
        'config_name': config['name'],
        'config_link': config['link'],
        'config_code': config['code'],
        'period': period,
        'issue_date': issue_date
    }
    users_db[str(user_id)]['used_configs'].append(used_config)
    save_data('users.json', users_db)

    try:
        bot.send_message(
            user_id,
            f"🔐 Ваш конфиг для подписки на {period.replace('_', ' ')}:\n"
            f"Название: {config['name']}\n"
            f"Ссылка: {config['link']}\n"
            f"Код: {config['code']}\n"
            f"Выдан: {issue_date}",
            parse_mode='Markdown'
        )
        return True, "Конфиг успешно отправлен"
    except Exception as e:
        return False, str(e)

# --- Инициализация бота ---
bot = telebot.TeleBot(TOKEN)

# --- Обработчики команд ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    if user_id not in users_db:
        users_db[user_id] = {
            'first_name': message.from_user.first_name,
            'username': message.from_user.username,
            'balance': 0,
            'subscription_end': None,
            'used_configs': [],
            'referrals_count': 0,
            'referred_by': None
        }
        save_data('users.json', users_db)

    if MAINTENANCE_MODE and user_id != str(ADMIN_ID):
        bot.reply_to(message, "Бот находится на техническом обслуживании. Пожалуйста, попробуйте позже.")
        return

    bot.send_message(message.chat.id, "Добро пожаловать!", reply_markup=main_menu_keyboard(user_id))

# --- Обработчики callback_query ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)

    if MAINTENANCE_MODE and user_id != str(ADMIN_ID):
        bot.answer_callback_query(call.id, "Бот находится на техническом обслуживании. Пожалуйста, попробуйте позже.")
        return

    # - Главное меню и покупка VPN -
    if call.data == "main_menu":
        bot.edit_message_text(
            "Главное меню:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=main_menu_keyboard(user_id)
        )
    elif call.data == "buy_vpn":
        bot.edit_message_text(
            "Выберите срок подписки:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=buy_vpn_keyboard()
        )
    elif call.data.startswith("choose_period_"):
        period_data_key = call.data.replace("choose_period_", "")
        amount = SUBSCRIPTION_PERIODS[period_data_key]['price']
        user_balance = users_db.get(user_id, {}).get('balance', 0)

        bot.edit_message_text(
            f"Вы выбрали подписку на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней.\n"
            f"Стоимость: {amount} ₽\n"
            f"Ваш баланс: {user_balance} ₽\n"
            f"Выберите способ оплаты:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=payment_methods_keyboard(period_data_key, amount, user_balance)
        )
    elif call.data.startswith("pay_card_"):
        # Извлекаем данные из callback_data: pay_card_{period}_{amount}
        parts = call.data.split('_')
        if len(parts) < 4:
            bot.edit_message_text("❌ Неверные данные оплаты.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return
        period_data_key = parts[2]
        amount_str = parts[3]
        try:
            amount = int(amount_str)
        except ValueError:
            bot.edit_message_text("❌ Неверная сумма оплаты.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return

        bot.edit_message_text(
            f"Для оплаты {amount} ₽ за подписку на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней:\n"
            f"1. Переведите {amount} ₽ на карту: `{CARD_NUMBER}`\n"
            f"Держатель: `{CARD_HOLDER}`\n"
            f"2. **ОБЯЗАТЕЛЬНО** отправьте скриншот перевода в этот чат.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown'
        )
    elif call.data.startswith("pay_stars_"):
        # Извлекаем данные из callback_data: pay_stars_{period}_{amount}
        parts = call.data.split('_')
        if len(parts) < 4:
            bot.edit_message_text("❌ Неверные данные оплаты.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return
        period_data_key = parts[2]
        amount_str = parts[3]
        try:
            amount = int(amount_str)
        except ValueError:
            bot.edit_message_text("❌ Неверная сумма оплаты.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return

        stars_amount = int(amount / STARS_TO_RUB)
        try:
            prices = [types.LabeledPrice(label=f"VPN подписка на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней", amount=stars_amount)]
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"VPN подписка на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней",
                description=f"Оплата подписки на VPN на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней",
                provider_token='',  # Здесь должен быть токен вашего провайдера Stars (если используете)
                currency='XTR',  # Валюта Telegram Stars
                prices=prices,
                start_parameter=f'vpn_subscription_{period_data_key}',
                invoice_payload=f'stars_payment_{period_data_key}_{amount}'
            )
        except Exception as e:
            bot.edit_message_text(
                f"Ошибка при создании платежа Stars: {e}\n"
                f"Пожалуйста, используйте оплату картой.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=payment_methods_keyboard(period_data_key, amount, users_db.get(user_id, {}).get('balance', 0))
            )
            return # Важно выйти, чтобы остальной код не выполнялся
    elif call.data.startswith("pay_balance_"):
        period_data_key = call.data.replace("pay_balance_", "")
        amount = SUBSCRIPTION_PERIODS[period_data_key]['price']
        user_balance = users_db.get(user_id, {}).get('balance', 0)

        if user_balance >= amount:
            # Обновляем баланс
            users_db[user_id]['balance'] = user_balance - amount
            # Продлеваем/устанавливаем подписку
            current_end = users_db[user_id].get('subscription_end')
            now = datetime.datetime.now()
            if current_end:
                try:
                    current_end_dt = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    current_end_dt = now
            else:
                current_end_dt = now
            new_end = current_end_dt + datetime.timedelta(days=SUBSCRIPTION_PERIODS[period_data_key]['days'])
            if current_end_dt < now: # Если подписка истекла, начинаем с текущего момента
                new_end = now + datetime.timedelta(days=SUBSCRIPTION_PERIODS[period_data_key]['days'])
            users_db[user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            save_data('users.json', users_db)

            # Пытаемся выдать конфиг
            success, result = send_config_to_user(user_id, period_data_key, call.from_user.username or 'user', call.from_user.first_name or 'User')

            if success:
                bot.edit_message_text(
                    f"✅ Оплата прошла успешно!\n"
                    f"💳 Списано с баланса: {amount} ₽\n"
                    f"💰 Остаток на балансе: {users_db[user_id].get('balance', 0)} ₽\n"
                    f"📅 Подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                    f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )
            else:
                bot.edit_message_text(
                    f"✅ Оплата прошла успешно, но возникла ошибка при выдаче конфига: {result}\n"
                    f"Обратитесь в поддержку: {ADMIN_USERNAME}",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )
        else:
            bot.edit_message_text("❌ Недостаточно средств на балансе.", chat_id=call.message.chat.id, message_id=call.message.message_id)
    elif call.data.startswith("pay_balance_partial_"):
        # Извлекаем данные из callback_data: pay_balance_partial_{period}_{total_amount}
        parts = call.data.split('_')
        if len(parts) < 4:
            bot.edit_message_text("❌ Неверные данные оплаты.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return
        period_data_key = parts[3]
        total_amount_str = parts[4]
        try:
            total_amount = int(total_amount_str)
        except ValueError:
            bot.edit_message_text("❌ Неверная сумма оплаты.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return

        user_balance = users_db.get(user_id, {}).get('balance', 0)
        needed_amount = max(0, total_amount - user_balance)

        if needed_amount > 0:
            # Сначала списываем с баланса
            users_db[user_id]['balance'] = 0
            # Сохраняем промежуточное состояние или используем временное хранилище
            # Для простоты, сохраним и продолжим процесс оплаты оставшейся суммы
            save_data('users.json', users_db)

            # Теперь запрашиваем оплату оставшейся суммы картой
            bot.edit_message_text(
                f"С баланса списано {user_balance} ₽.\n"
                f"Осталось оплатить: {needed_amount} ₽.\n"
                f"Для оплаты {needed_amount} ₽ за подписку на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней:\n"
                f"1. Переведите {needed_amount} ₽ на карту: `{CARD_NUMBER}`\n"
                f"Держатель: `{CARD_HOLDER}`\n"
                f"2. **ОБЯЗАТЕЛЬНО** отправьте скриншот перевода в этот чат.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='Markdown'
            )
        else:
            # Вся сумма покрыта балансом (крайний случай, но возможен если баланс > total_amount)
            # Обновляем баланс
            users_db[user_id]['balance'] = user_balance - total_amount
            # Продлеваем/устанавливаем подписку
            current_end = users_db[user_id].get('subscription_end')
            now = datetime.datetime.now()
            if current_end:
                try:
                    current_end_dt = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    current_end_dt = now
            else:
                current_end_dt = now
            new_end = current_end_dt + datetime.timedelta(days=SUBSCRIPTION_PERIODS[period_data_key]['days'])
            if current_end_dt < now:
                new_end = now + datetime.timedelta(days=SUBSCRIPTION_PERIODS[period_data_key]['days'])
            users_db[user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            save_data('users.json', users_db)

            # Пытаемся выдать конфиг
            success, result = send_config_to_user(user_id, period_data_key, call.from_user.username or 'user', call.from_user.first_name or 'User')

            if success:
                bot.edit_message_text(
                    f"✅ Оплата прошла успешно!\n"
                    f"💳 Списано с баланса: {total_amount} ₽\n"
                    f"💰 Остаток на балансе: {users_db[user_id].get('balance', 0)} ₽\n"
                    f"📅 Подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                    f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )
            else:
                bot.edit_message_text(
                    f"✅ Оплата прошла успешно, но возникла ошибка при выдаче конфига: {result}\n"
                    f"Обратитесь в поддержку: {ADMIN_USERNAME}",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )

    elif call.data == "my_configs":
        # Проверяем, есть ли у пользователя выданные конфиги
        user_info = users_db.get(user_id, {})
        used_configs = user_info.get('used_configs', [])
        if used_configs:
            message_text = f"🔐 **Ваши выданные конфиги:**\n"
            config_count = 0
            for i, config in enumerate(used_configs, 1): # Исправлен отсчет для читаемости
                config_count += 1
                message_text += f" {i}. {config['config_name']} ({config['period']})\n"
                message_text += f" Ссылка: {config['config_link']}\n"
                message_text += f" Выдан: {config['issue_date']}\n"
            if config_count == 0:
                message_text = "❌ Нет выданных конфигов."
            bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')
        else:
            bot.send_message(call.message.chat.id, "❌ У вас нет выданных конфигов.", reply_markup=my_configs_keyboard(user_id))

    elif call.data.startswith("get_config_"):
        period_data_key = call.data.replace("get_config_", "")
        if period_data_key in SUBSCRIPTION_PERIODS:
            username = call.from_user.username or 'user'
            first_name = call.from_user.first_name or 'User'
            success, result = send_config_to_user(user_id, period_data_key, username, first_name)
            if success:
                bot.answer_callback_query(call.id, f"Конфиг на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней выдан! Проверьте сообщения.")
            else:
                bot.answer_callback_query(call.id, f"Ошибка при выдаче конфига: {result}")
        else:
            bot.answer_callback_query(call.id, "Неверный период подписки.")

    # --- Админка ---
    elif call.data == "admin_panel":
        if user_id == str(ADMIN_ID):
            # Пример клавиатуры админ-панели
            admin_markup = types.InlineKeyboardMarkup(row_width=1)
            admin_markup.add(
                types.InlineKeyboardButton("Активные пользователи", callback_data="admin_active_users"),
                types.InlineKeyboardButton("Все пользователи", callback_data="admin_all_users"),
                types.InlineKeyboardButton("Найти пользователя", callback_data="admin_search_user"),
                types.InlineKeyboardButton("Рассылка", callback_data="admin_broadcast"),
                types.InlineKeyboardButton("Назад", callback_data="main_menu")
            )
            bot.edit_message_text("Админ-панель:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_markup)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_active_users":
        if user_id == str(ADMIN_ID):
            message_text = "**Активные пользователи (с подпиской):**\n"
            active_users_list = []
            for uid, u_data in users_db.items():
                if u_data.get('subscription_end'):
                    try:
                        sub_end = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                        if sub_end > datetime.datetime.now():
                            active_users_list.append((uid, u_data))
                    except ValueError:
                        pass # Игнорировать некорректные даты

            if not active_users_list:
                message_text = "❌ Нет активных пользователей."
            else:
                for uid, u_data in active_users_list:
                    referred_by = "Нет"
                    if u_data.get('referred_by'):
                        referrer = users_db.get(u_data['referred_by'], {})
                        referred_by = f"@{referrer.get('username', 'N/A')} (ID: `{u_data['referred_by']}`)"
                    # Формируем строку для каждого пользователя
                    sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y %H:%M')}"
                    message_text += f"👤 **{u_data.get('first_name', 'N/A')}** (@{u_data.get('username', 'N/A')})\n"
                    message_text += f" 🆔: `{uid}`| {sub_status}\n"
                    message_text += f" 💰: {u_data.get('balance', 0)} ₽| 🤝: {u_data.get('referrals_count', 0)}\n"
                    message_text += f" 📎 Приглашен: {referred_by}\n"
                    message_text += f" ⚡ /manage_{uid}\n" # Добавлена команда для быстрого управления

            bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_all_users":
        if user_id == str(ADMIN_ID):
            message_text = f"**Все пользователи ({len(users_db)}):**\n"
            user_entries = []
            for uid, u_data in users_db.items():
                sub_status = "❌ Нет подписки"
                if u_data.get('subscription_end'):
                    try:
                        sub_end = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                        if sub_end > datetime.datetime.now():
                            sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y %H:%M')}"
                        else:
                            sub_status = "❌ Истекла"
                    except ValueError:
                        sub_status = "❌ Некорректная дата"
                # Формируем строку для каждого пользователя
                user_entries.append(
                    f"👤 **{u_data.get('first_name', 'N/A')}** (@{u_data.get('username', 'N/A')})\n"
                    f" 🆔: `{uid}`| {sub_status}\n"
                    f" 💰: {u_data.get('balance', 0)} ₽| 🤝: {u_data.get('referrals_count', 0)}\n"
                    f" ⚡ /manage_{uid}\n"
                )

            # Разбиваем на чанки по 10 пользователей
            current_chunk = []
            for i, entry in enumerate(user_entries):
                current_chunk.append(entry)
                if (i + 1) % 10 == 0 or (i + 1) == len(user_entries):
                    chunk_text = message_text + "".join(current_chunk)
                    bot.send_message(call.message.chat.id, chunk_text, parse_mode='Markdown')
                    current_chunk = [] # Сбрасываем чанк
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_search_user":
        if user_id == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите ID, имя пользователя или имя пользователя для поиска:")
            # Здесь можно использовать FSM или временный словарь для хранения состояния
            # current_admin_action_data[user_id] = {'action': 'search_user'}
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_broadcast":
        if user_id == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите текст для рассылки всем пользователям:")
            # current_admin_action_data[user_id] = {'action': 'broadcast'}
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    else:
        bot.answer_callback_query(call.id, "Неизвестная команда.")

# --- Обработчик скриншотов ---
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = str(message.from_user.id)

    if MAINTENANCE_MODE and user_id != str(ADMIN_ID):
        bot.reply_to(message, "Бот находится на техническом обслуживании. Пожалуйста, попробуйте позже.")
        return

    # Проверяем, есть ли текст в сообщении, который может содержать сумму
    caption = message.caption if message.caption else ""
    # Простая проверка: содержит ли текст "руб" или "₽" и цифры
    import re
    amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:₽|руб)', caption, re.IGNORECASE)
    if not amount_match:
        # Проверяем текст в предыдущем сообщении, если оно есть
        # (например, если скрин отправлен сразу после инструкции)
        # Для простоты, предположим, что сумма не найдена
        bot.reply_to(message, "❌ Скриншот получен, но не удалось определить сумму оплаты. Пожалуйста, укажите сумму в комментарии к фото или отправьте снова с пометкой.")
        return

    amount_paid = float(amount_match.group(1))
    # Здесь должна быть логика проверки суммы и связывания с пользователем
    # Пока что просто сохраняем в базу платежей как "ожидающий подтверждения"
    payment_id = f"card_{user_id}_{int(time.time())}"
    payments_db[payment_id] = {
        'user_id': user_id,
        'amount': amount_paid,
        'status': 'pending',
        'timestamp': time.time(),
        'photo_id': message.photo[-1].file_id # Сохраняем ID самого большого фото
    }
    save_data('payments.json', payments_db)

    bot.reply_to(message, f"✅ Скриншот оплаты на {amount_paid} ₽ получен. Ожидайте подтверждения администратором. ID платежа: {payment_id}")

# --- Обработчик текстовых сообщений для админов (например, /manage_USER_ID) ---
@bot.message_handler(func=lambda message: message.text.startswith('/manage_') or (str(message.from_user.id) == str(ADMIN_ID) and current_admin_action_data.get(str(message.from_user.id))))
def handle_admin_commands(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        bot.reply_to(message, "У вас нет прав администратора.")
        return

    # Проверяем, находится ли админ в процессе какого-то действия
    admin_user_id = str(message.from_user.id)
    current_action = current_admin_action_data.get(admin_user_id)

    if current_action:
        action_type = current_action.get('action')
        if action_type == 'search_user':
            search_query = message.text.strip()
            found_users = []
            for uid, user_data in users_db.items():
                if (search_query == uid or
                    search_query.lstrip('@') == user_data.get('username', '') or
                    search_query.lower() in user_data.get('first_name', '').lower()):
                    found_users.append((uid, user_data))

            if found_users:
                message_text = f"**Найдено пользователей: {len(found_users)}**\n"
                for uid, user_data in found_users:
                    sub_status = "❌ Нет подписки"
                    if user_data.get('subscription_end'):
                        try:
                            sub_end = datetime.datetime.strptime(user_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                            if sub_end > datetime.datetime.now():
                                sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y')}"
                            else:
                                sub_status = "❌ Истекла"
                        except ValueError:
                            sub_status = "❌ Некорректная дата"
                    message_text += f"👤 **{user_data.get('first_name', 'N/A')}** (@{user_data.get('username', 'N/A')})\n"
                    message_text += f"🆔 ID: `{uid}`\n"
                    message_text += f"📊 {sub_status}| 💰 {user_data.get('balance', 0)} ₽\n"
                    message_text += f"⚡ `/manage_{uid}`\n"
                bot.send_message(message.chat.id, message_text, parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id, "❌ Пользователи не найдены.")

            # Очищаем состояние
            current_admin_action_data.pop(admin_user_id, None)

        elif action_type == 'broadcast':
            broadcast_text = message.text
            sent_count = 0
            failed_count = 0
            bot.send_message(message.chat.id, "📢 Начинаю рассылку...")

            for uid in users_db.keys():
                try:
                    bot.send_message(uid, f"📢 **Объявление от администратора:**\n{broadcast_text}", parse_mode='Markdown')
                    sent_count += 1
                    time.sleep(0.1)  # Небольшая задержка, чтобы избежать лимитов Telegram
                except Exception as e:
                    print(f"Не удалось отправить сообщение пользователю {uid}: {e}")
                    failed_count += 1

            bot.send_message(message.chat.id, f"✅ Рассылка завершена!\n📤 Отправлено: {sent_count}\n❌ Ошибок: {failed_count}")
            current_admin_action_data.pop(admin_user_id, None)

        elif action_type == 'edit_user_balance' or action_type == 'edit_user_subscription':
            # Обработка ввода нового баланса или даты подписки
            target_user_id = current_action.get('target_user_id')
            if not target_user_id or target_user_id not in users_db:
                bot.send_message(message.chat.id, "❌ Пользователь не найден или данные устарели.")
                current_admin_action_data.pop(admin_user_id, None)
                return

            if action_type == 'edit_user_balance':
                try:
                    new_balance = int(message.text.strip())
                    users_db[target_user_id]['balance'] = new_balance
                    save_data('users.json', users_db)
                    bot.send_message(message.chat.id, f"✅ Баланс пользователя {target_user_id} обновлен на {new_balance} ₽.")
                    # Отправляем уведомление пользователю
                    try:
                        bot.send_message(target_user_id, f"💰 Ваш баланс был изменен администратором. Новый баланс: {new_balance} ₽.")
                    except:
                        pass # Игнорировать ошибку, если не удалось отправить
                except ValueError:
                    bot.send_message(message.chat.id, "❌ Пожалуйста, введите корректное число для баланса.")
            elif action_type == 'edit_user_subscription':
                new_subscription = message.text.strip()
                if new_subscription.lower() == 'нет':
                    users_db[target_user_id]['subscription_end'] = None
                    save_data('users.json', users_db)
                    bot.send_message(message.chat.id, f"✅ Подписка пользователя {target_user_id} удалена.")
                    try:
                        bot.send_message(target_user_id, "❌ Ваша подписка была удалена администратором.")
                    except:
                        pass
                else:
                    try:
                        # Пытаемся распознать формат даты, например, 'YYYY-MM-DD HH:MM:SS' или 'DD.MM.YYYY'
                        parsed_date = None
                        for fmt in ('%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M', '%d.%m.%Y'):
                            try:
                                parsed_date = datetime.datetime.strptime(new_subscription, fmt)
                                break
                            except ValueError:
                                continue
                        if parsed_date:
                            users_db[target_user_id]['subscription_end'] = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                            save_data('users.json', users_db)
                            bot.send_message(message.chat.id, f"✅ Подписка пользователя {target_user_id} обновлена до {parsed_date.strftime('%d.%m.%Y %H:%M')}.")
                            try:
                                bot.send_message(target_user_id, f"📅 Ваша подписка была обновлена администратором до {parsed_date.strftime('%d.%m.%Y %H:%M')}.")
                            except:
                                pass
                        else:
                            raise ValueError("Неподдерживаемый формат даты")
                    except ValueError:
                        bot.send_message(message.chat.id, "❌ Неверный формат даты. Используйте YYYY-MM-DD HH:MM:SS или DD.MM.YYYY.")

            # Очищаем состояние
            current_admin_action_data.pop(admin_user_id, None)

    elif message.text.startswith('/manage_'):
        # Команда /manage_USER_ID
        try:
            parts = message.text.split('_')
            if len(parts) < 2:
                bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: `/manage_USER_ID`", parse_mode='Markdown')
                return
            target_user_id = parts[1]

            if target_user_id in users_db:
                user_info = users_db[target_user_id]
                sub_status = "❌ Нет подписки"
                if user_info.get('subscription_end'):
                    try:
                        sub_end = datetime.datetime.strptime(user_info['subscription_end'], '%Y-%m-%d %H:%M:%S')
                        if sub_end > datetime.datetime.now():
                            sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y %H:%M')}"
                        else:
                            sub_status = "❌ Истекла"
                    except ValueError:
                        sub_status = "❌ Некорректная дата"

                message_text = f"👤 **Редактирование пользователя:**\n"
                message_text += f"**Имя:** {user_info.get('first_name', 'N/A')}\n"
                message_text += f"**Username:** @{user_info.get('username', 'N/A')}\n"
                message_text += f"**ID:** `{target_user_id}`\n"
                message_text += f"**Баланс:** {user_info.get('balance', 0)} ₽\n"
                message_text += f"**Подписка:** {sub_status}\n"

                # Клавиатура для действий с пользователем
                user_action_markup = types.InlineKeyboardMarkup(row_width=1)
                user_action_markup.add(
                    types.InlineKeyboardButton("Изменить баланс", callback_data=f"admin_edit_balance_{target_user_id}"),
                    types.InlineKeyboardButton("Изменить подписку", callback_data=f"admin_edit_subscription_{target_user_id}"),
                    types.InlineKeyboardButton("Назад", callback_data="admin_panel")
                )

                bot.send_message(message.chat.id, message_text, reply_markup=user_action_markup, parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id, "❌ Пользователь не найден.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка при обработке команды: {e}")

# --- Временное хранилище для состояния админских действий ---
current_admin_action_data = {}

# --- Обработчики callback_query для админ-панели (редактирование) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_edit_balance_') or call.data.startswith('admin_edit_subscription_'))
def handle_admin_edit_actions(call):
    user_id = str(call.from_user.id)
    if user_id != str(ADMIN_ID):
        bot.answer_callback_query(call.id, "У вас нет прав администратора.")
        return

    if call.data.startswith('admin_edit_balance_'):
        target_user_id = call.data.replace('admin_edit_balance_', '')
        bot.send_message(call.message.chat.id, f"Введите новый баланс для пользователя {target_user_id}:")
        current_admin_action_data[user_id] = {'action': 'edit_user_balance', 'target_user_id': target_user_id}
    elif call.data.startswith('admin_edit_subscription_'):
        target_user_id = call.data.replace('admin_edit_subscription_', '')
        bot.send_message(call.message.chat.id, f"Введите новую дату окончания подписки для пользователя {target_user_id} в формате YYYY-MM-DD HH:MM:SS или DD.MM.YYYY, или 'нет' для удаления:")
        current_admin_action_data[user_id] = {'action': 'edit_user_subscription', 'target_user_id': target_user_id}

    bot.answer_callback_query(call.id)

# --- Обработчик успешной оплаты Stars ---
@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout_query(pre_checkout_query):
    try:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    except Exception as e:
        print(f"Ошибка при обработке pre_checkout_query: {e}")

@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    user_id = str(message.from_user.id)
    payment_info = message.successful_payment
    # invoice_payload в формате 'stars_payment_{period}_{amount}'
    payload = payment_info.invoice_payload
    if payload.startswith('stars_payment_'):
        parts = payload.split('_')
        if len(parts) >= 4 and parts[0] == 'stars_payment':
            period_data_key = parts[2]
            original_amount_rub_str = parts[3]
            try:
                original_amount_rub = int(original_amount_rub_str)
            except ValueError:
                print(f"Неверная сумма в payload: {payload}")
                return

            # Обновляем баланс пользователя или сразу выдаём подписку
            # В данном случае, предположим, что оплата Stars сразу активирует подписку
            current_end = users_db[user_id].get('subscription_end')
            now = datetime.datetime.now()
            if current_end:
                try:
                    current_end_dt = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    current_end_dt = now
            else:
                current_end_dt = now
            new_end = current_end_dt + datetime.timedelta(days=SUBSCRIPTION_PERIODS[period_data_key]['days'])
            if current_end_dt < now: # Если подписка истекла, начинаем с текущего момента
                new_end = now + datetime.timedelta(days=SUBSCRIPTION_PERIODS[period_data_key]['days'])
            users_db[user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            save_data('users.json', users_db)

            # Пытаемся выдать конфиг
            success, result = send_config_to_user(user_id, period_data_key, message.from_user.username or 'user', message.from_user.first_name or 'User')

            if success:
                 bot.send_message(message.chat.id, f"✅ Оплата прошла успешно!\n"
                                                 f"🪙 Списано: {payment_info.total_amount} {payment_info.currency}\n"
                                                 f"📅 Подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                                 f"🔐 Конфиг уже выдан! Проверьте сообщения выше.")
            else:
                 bot.send_message(message.chat.id, f"✅ Оплата прошла успешно, но возникла ошибка при выдаче конфига: {result}\n"
                                                 f"Обратитесь в поддержку: {ADMIN_USERNAME}")

            # Уведомление администратору
            bot.send_message(ADMIN_ID, f"✅ Успешная оплата Stars: {payment_info.total_amount} {payment_info.currency}\n"
                                     f"На сумму: {original_amount_rub} ₽\n"
                                     f"От: @{message.from_user.username} (ID: `{user_id}`)\n"
                                     f"Период: {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней",
                                     parse_mode='Markdown')
        else:
            print(f"Неверный формат payload: {payload}")
    else:
        # Если оплата не Stars, возможно, это другая валюта или обработка через провайдера
        print(f"Получена оплата не через Stars: {payload}")
        bot.send_message(message.chat.id, "❌ Этот бот принимает оплату только через Telegram Stars или карту.")

print("Бот запущен...")
print("="*80 + "")
print("ВНИМАНИЕ: ADMIN_ID не изменен. Пожалуйста, замените '8320218178' на ваш фактический Telegram ID в коде.")
print("Без этого админ-панель не будет работать корректно!")
print("Чтобы узнать свой ID, напишите @userinfobot в Telegram.")
print("="*80 + "")

try:
    bot.polling(none_stop=True, interval=0, timeout=60)
except KeyboardInterrupt:
    print("Бот остановлен пользователем (Ctrl+C).")
except Exception as e:
    print(f"Произошла ошибка: {e}")
    print("Бот будет перезапущен, если настроен через systemd.")
