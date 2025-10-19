--- START OF FILE ai_studio_code (3).py ---

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

# --- КОНСТАНТЫ ---
TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY'
ADMIN_USERNAME = '@Gl1ch555'
ADMIN_ID = 8320218178 # Ваш ID, который вы предоставили
CARD_NUMBER = '2204320690808227'
CARD_HOLDER = 'Makarov Pavel Alexandrovich (Ozon Bank)'

PRICE_MONTH = 50
PRICE_2_MONTHS = 90 # Со скидкой
PRICE_3_MONTHS = 120 # Со скидкой

REFERRAL_BONUS_INVITER_RUB = 25 # Бонус пригласившему (на баланс)
REFERRAL_BONUS_INVITER_DAYS = 7 # Бонус пригласившему (дни подписки)
REFERRAL_BONUS_NEW_USER_RUB = 50 # Бонус новому пользователю при регистрации по реф. ссылке

# Курс Stars (1 звезда = 1.5 рубля)
STARS_TO_RUB = 1.5

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = telebot.TeleBot(TOKEN)

# --- БАЗЫ ДАННЫХ (ПРОСТОЙ JSON) ---
def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

users_db = load_data('users.json')
configs_db = load_data('configs.json')
payments_db = load_data('payments.json')

# --- МОДЕЛИ ДАННЫХ ---
# users_db: { user_id: { 'balance': 0, 'subscription_end': None, 'referred_by': None, 'username': '...', 'first_name': '...', 'referrals_count': 0, 'used_configs': [], 'first_purchase_made': False } }
# configs_db: { '1_month': [ { 'name': 'Germany 1', 'image': 'url_to_image', 'code': 'config_code', 'link': 'link_to_config', 'added_by': 'admin_username', 'is_used': False }, ... ], '2_months': [], '3_months': [] }
# payments_db: { payment_id: { 'user_id': ..., 'amount': ..., 'status': 'pending/confirmed/rejected', 'screenshot_id': ..., 'timestamp': ..., 'period': ..., 'method': 'card/stars', 'balance_used': 0 } }

# --- ГЕНЕРАТОР УНИКАЛЬНОГО ID ДЛЯ ПЛАТЕЖЕЙ ---
def generate_payment_id():
    return str(int(time.time() * 100000))

# --- Хелпер для получения цены по периоду ---
def get_price_for_period(period):
    if period == "1_month":
        return PRICE_MONTH
    elif period == "2_months":
        return PRICE_2_MONTHS
    elif period == "3_months":
        return PRICE_3_MONTHS
    return 0

# --- ФУНКЦИИ АДМИНКИ ---
def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Управление конфигами", callback_data="admin_manage_configs"),
        types.InlineKeyboardButton("Подтвердить платежи", callback_data="admin_confirm_payments"),
        types.InlineKeyboardButton("Список пользователей", callback_data="admin_users_list"),
        types.InlineKeyboardButton("Управление пользователями", callback_data="admin_manage_users"),
        types.InlineKeyboardButton("Управление конфигами пользователей", callback_data="admin_manage_user_configs"),
        types.InlineKeyboardButton("Рассылка", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("Удалить все конфиги", callback_data="admin_delete_all_configs"), # Новая кнопка
        types.InlineKeyboardButton("Назад в меню", callback_data="main_menu")
    )
    return markup

def manage_configs_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Добавить конфиг", callback_data="admin_add_config"),
        types.InlineKeyboardButton("Удалить конфиг", callback_data="admin_delete_config"),
        types.InlineKeyboardButton("Показать конфиги", callback_data="admin_show_configs"),
        types.InlineKeyboardButton("Назад в админку", callback_data="admin_panel")
    )
    return markup

def choose_period_keyboard(action):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("1 месяц", callback_data=f"{action}_1_month"),
        types.InlineKeyboardButton("2 месяца", callback_data=f"{action}_2_months"),
        types.InlineKeyboardButton("3 месяца", callback_data=f"{action}_3_months"),
        types.InlineKeyboardButton("Назад", callback_data="admin_manage_configs")
    )
    return markup

def confirm_payments_keyboard(payment_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Подтвердить", callback_data=f"admin_confirm_{payment_id}"),
        types.InlineKeyboardButton("Отклонить", callback_data=f"admin_reject_{payment_id}")
    )
    return markup

def user_configs_management_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Показать все выданные конфиги", callback_data="admin_show_user_configs"),
        types.InlineKeyboardButton("Удалить конфиг пользователя", callback_data="admin_delete_user_config"),
        types.InlineKeyboardButton("Перевыдать конфиг", callback_data="admin_reissue_config"),
        types.InlineKeyboardButton("Назад в админку", callback_data="admin_panel")
    )
    return markup

def users_management_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Активные пользователи", callback_data="admin_active_users"),
        types.InlineKeyboardButton("Все пользователи", callback_data="admin_all_users"),
        types.InlineKeyboardButton("Поиск пользователя", callback_data="admin_search_user"),
        types.InlineKeyboardButton("Изменить баланс/подписку", callback_data="admin_edit_user"),
        types.InlineKeyboardButton("Назад в админку", callback_data="admin_panel")
    )
    return markup

def user_action_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Изменить баланс", callback_data=f"admin_edit_balance_{user_id}"),
        types.InlineKeyboardButton("Изменить подписку", callback_data=f"admin_edit_subscription_{user_id}"),
        types.InlineKeyboardButton("Просмотреть конфиги", callback_data=f"admin_view_user_configs_{user_id}"),
        types.InlineKeyboardButton("Назад к списку", callback_data="admin_manage_users")
    )
    return markup

# --- ФУНКЦИИ ПОЛЬЗОВАТЕЛЯ ---
def main_menu_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Купить VPN 🚀", callback_data="buy_vpn"),
        types.InlineKeyboardButton("Личный кабинет 👤", callback_data="my_account"),
        types.InlineKeyboardButton("Поддержка 👨‍💻", callback_data="support"),
        types.InlineKeyboardButton("Реферальная система 🤝", callback_data="referral_system")
    )
    if str(user_id) == str(ADMIN_ID):
        markup.add(types.InlineKeyboardButton("Админ-панель 🛠️", callback_data="admin_panel"))
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

def payment_options_keyboard(period_data, amount_to_pay, user_balance):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Оплата с баланса, если достаточно средств
    if user_balance >= amount_to_pay:
        markup.add(types.InlineKeyboardButton(f"Оплатить с баланса ({amount_to_pay} ₽)", callback_data=f"pay_balance_{period_data}_{amount_to_pay}"))
    else:
        # Частичная оплата с баланса + доплата
        remaining_amount = amount_to_pay - user_balance
        if user_balance > 0:
            markup.add(types.InlineKeyboardButton(f"Оплатить с баланса ({user_balance} ₽) + Доплата ({remaining_amount} ₽)", callback_data=f"confirm_partial_payment_{period_data}_{amount_to_pay}"))
        else:
            # Оплата без использования баланса
            markup.add(types.InlineKeyboardButton(f"Оплата картой ({amount_to_pay} ₽)", callback_data=f"pay_card_{period_data}_{amount_to_pay}"))
            
            stars_amount = int(amount_to_pay / STARS_TO_RUB)
            if stars_amount > 0:
                markup.add(types.InlineKeyboardButton(f"Оплата Telegram Stars ({stars_amount} Stars)", callback_data=f"pay_stars_{period_data}_{amount_to_pay}"))
    
    markup.add(types.InlineKeyboardButton("Назад", callback_data="buy_vpn"))
    return markup

# Клавиатура для выбора способа доплаты
def surcharge_methods_keyboard(period_data, total_amount, balance_used):
    markup = types.InlineKeyboardMarkup(row_width=1)
    remaining_amount = total_amount - balance_used
    
    markup.add(types.InlineKeyboardButton(f"Оплата картой ({remaining_amount} ₽)", callback_data=f"pay_card_{period_data}_{total_amount}_{balance_used}"))
    
    stars_amount = int(remaining_amount / STARS_TO_RUB)
    if stars_amount > 0:
        markup.add(types.InlineKeyboardButton(f"Оплата Telegram Stars ({stars_amount} Stars)", callback_data=f"pay_stars_{period_data}_{total_amount}_{balance_used}"))
    
    markup.add(types.InlineKeyboardButton("Назад", callback_data=f"choose_period_{period_data}")) # Вернуться к выбору периода
    return markup


def my_account_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Мои конфиги", callback_data="my_configs"),
        types.InlineKeyboardButton("Продлить подписку", callback_data="buy_vpn"),
        types.InlineKeyboardButton("Назад", callback_data="main_menu")
    )
    return markup

def my_configs_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Получаем активные подписки пользователя
    user_info = users_db.get(str(user_id), {})
    subscription_end = user_info.get('subscription_end')
    
    if subscription_end:
        end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
        if end_date > datetime.datetime.now():
            # Показываем кнопки для каждого периода, если есть активные конфиги
            for period_key in ['1_month', '2_months', '3_months']:
                if any(cfg['period'] == period_key for cfg in user_info.get('used_configs', [])):
                     markup.add(types.InlineKeyboardButton(f"Показать мой конфиг на {period_key.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}", callback_data=f"show_my_config_{period_key}"))
    
    markup.add(types.InlineKeyboardButton("Назад", callback_data="my_account"))
    return markup

# --- ФУНКЦИЯ ВЫДАЧИ/ПОКАЗА КОНФИГА ---
def get_or_send_config_to_user(user_id, period, username, first_name):
    """
    Выдает новый конфиг пользователю или возвращает уже выданный, если есть.
    Сохраняет информацию о выдаче и помечает конфиг как использованный.
    """
    user_info = users_db[str(user_id)]
    
    # Сначала проверяем, есть ли у пользователя уже выданный конфиг для этого периода
    for used_config in user_info.get('used_configs', []):
        if used_config['period'] == period:
            return True, used_config # Возвращаем уже выданный конфиг

    # Если нет, ищем свободный конфиг в базе
    available_configs = [cfg for cfg in configs_db.get(period, []) if not cfg.get('is_used', False)]
    
    if not available_configs:
        return False, "Нет доступных конфигов для этого периода. Обратитесь к администратору."
    
    # Берем первый доступный конфиг
    config = available_configs[0]
    
    # Генерируем уникальное имя для конфига
    config_name_for_user = f"{first_name} ({username}) - {period.replace('_', ' ')}"
    
    # Сохраняем информацию о выданном конфиге в used_configs пользователя
    if 'used_configs' not in user_info:
        user_info['used_configs'] = []
    
    used_config_entry = {
        'config_name': config['name'], # Оригинальное имя из базы
        'config_link': config['link'],
        'config_code': config['code'],
        'period': period,
        'issue_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user_name': f"{first_name} (@{username})",
        'is_active': True # Помечаем, что этот конфиг активен
    }
    
    user_info['used_configs'].append(used_config_entry)
    
    # Помечаем конфиг как использованный в общей базе конфигов
    for cfg in configs_db[period]:
        if cfg['code'] == config['code']:
            cfg['is_used'] = True
            break
            
    save_data('users.json', users_db)
    save_data('configs.json', configs_db)
    
    return True, used_config_entry


# --- ОБРАБОТЧИК КОМАНДЫ /start ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username if message.from_user.username else 'N/A'
    first_name = message.from_user.first_name if message.from_user.first_name else 'N/A'

    if user_id not in users_db:
        referred_by_id = None
        
        # Проверяем, есть ли реферальный ID в сообщении
        if len(message.text.split()) > 1:
            try:
                potential_referrer_id = message.text.split()[1]
                # Убеждаемся, что реферер существует и это не сам пользователь
                if potential_referrer_id in users_db and potential_referrer_id != user_id:
                    referred_by_id = potential_referrer_id
            except ValueError:
                pass # Если реферальный ID некорректен

        users_db[user_id] = {
            'balance': REFERRAL_BONUS_NEW_USER_RUB if referred_by_id else 0, # Бонус новому пользователю
            'subscription_end': None,
            'referred_by': referred_by_id,
            'username': username,
            'first_name': first_name,
            'referrals_count': 0,
            'used_configs': [],
            'first_purchase_made': False # Для отслеживания первой покупки реферала
        }
        save_data('users.json', users_db)

        if referred_by_id:
            bot.send_message(user_id, f"🎉 Вы зарегистрировались по реферальной ссылке и получили {REFERRAL_BONUS_NEW_USER_RUB} ₽ на баланс!")

    bot.send_message(message.chat.id, "Привет! Добро пожаловать в VPN Bot!",
                     reply_markup=main_menu_keyboard(message.from_user.id))

# --- ОБРАБОТЧИК CALLBACK-КНОПОК ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    user_info = users_db.get(user_id, {})
    
    if call.data == "main_menu":
        bot.edit_message_text("Главное меню:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=main_menu_keyboard(user_id))
    
    # --- ПОКУПКА VPN ---
    elif call.data == "buy_vpn":
        bot.edit_message_text("Выберите срок подписки:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=buy_vpn_keyboard())
    
    elif call.data.startswith("choose_period_"):
        period_data = call.data.replace("choose_period_", "") # 1_month, 2_months, 3_months
        amount_to_pay = get_price_for_period(period_data)
        
        current_balance = user_info.get('balance', 0)
        
        message_text = (f"Вы выбрали подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}. "
                        f"К оплате: {amount_to_pay} ₽.\nВаш баланс: {current_balance} ₽.\n\n")
        
        if current_balance >= amount_to_pay:
            message_text += "Вы можете оплатить подписку полностью с баланса."
        elif current_balance > 0:
            remaining_amount = amount_to_pay - current_balance
            message_text += f"Вы можете оплатить {current_balance} ₽ с баланса и доплатить {remaining_amount} ₽."
        else:
            message_text += "Выберите способ оплаты."

        bot.edit_message_text(message_text,
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=payment_options_keyboard(period_data, amount_to_pay, current_balance))

    # --- Оплата полностью с баланса ---
    elif call.data.startswith("pay_balance_"):
        parts = call.data.split('_')
        period_data = f"{parts[2]}_{parts[3]}"
        amount_str = parts[4]
        total_amount = int(amount_str)
        
        current_balance = user_info.get('balance', 0)
        
        if current_balance >= total_amount:
            # Списываем с баланса
            users_db[user_id]['balance'] -= total_amount
            save_data('users.json', users_db)
            
            # Обновляем подписку
            update_user_subscription(user_id, period_data)

            # Регистрируем платеж
            payment_id = generate_payment_id()
            payments_db[payment_id] = {
                'user_id': user_id,
                'amount': total_amount,
                'status': 'confirmed',
                'screenshot_id': None,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period': period_data,
                'method': 'balance',
                'balance_used': total_amount
            }
            save_data('payments.json', payments_db)
            
            # Выдаем конфиг
            issue_config_and_notify_user(user_id, period_data)
            
            bot.edit_message_text(f"✅ Подписка на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')} успешно оплачена с баланса! "
                                  f"Ваш новый баланс: {users_db[user_id]['balance']} ₽.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=main_menu_keyboard(user_id))
            notify_admin_of_successful_payment(user_id, total_amount, period_data, 'balance', total_amount)
        else:
            bot.answer_callback_query(call.id, "Недостаточно средств на балансе. Попробуйте еще раз.")
            bot.edit_message_text("Возникла ошибка оплаты с баланса. Пожалуйста, попробуйте снова.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=buy_vpn_keyboard())

    # --- Подтверждение частичной оплаты ---
    elif call.data.startswith("confirm_partial_payment_"):
        parts = call.data.split('_')
        period_data = f"{parts[3]}_{parts[4]}"
        total_amount = int(parts[5])
        
        balance_used = min(user_info.get('balance', 0), total_amount)
        remaining_amount = total_amount - balance_used

        bot.edit_message_text(f"Вы используете {balance_used} ₽ с баланса.\n"
                              f"Необходимо доплатить {remaining_amount} ₽.\n"
                              f"Выберите способ доплаты:",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=surcharge_methods_keyboard(period_data, total_amount, balance_used))

    # --- Оплата картой (полная или доплата) ---
    elif call.data.startswith("pay_card_"):
        parts = call.data.split('_')
        period_data = f"{parts[2]}_{parts[3]}"
        total_amount = int(parts[4])
        balance_used = int(parts[5]) if len(parts) > 5 else 0 # Сколько было использовано с баланса
        
        amount_to_transfer = total_amount - balance_used
        
        # Списываем баланс сразу, если он использовался для частичной оплаты
        if balance_used > 0:
            users_db[user_id]['balance'] -= balance_used
            save_data('users.json', users_db)

        payment_id = generate_payment_id()
        payments_db[payment_id] = {
            'user_id': user_id,
            'amount': total_amount, # Общая сумма покупки
            'amount_to_transfer': amount_to_transfer, # Сумма для перевода по карте
            'status': 'pending',
            'screenshot_id': None,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'period': period_data,
            'method': 'card',
            'balance_used': balance_used
        }
        save_data('payments.json', payments_db)

        bot.edit_message_text(f"Для оплаты {amount_to_transfer} ₽ за подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}:"
                              f"\n\n1. Переведите {amount_to_transfer} ₽ на карту: `{CARD_NUMBER}`"
                              f"\nДержатель: `{CARD_HOLDER}`"
                              f"\n\n2. **ОБЯЗАТЕЛЬНО** отправьте скриншот перевода в этот чат."
                              f"\n\nПосле получения скриншота администратор проверит платеж и подтвердит вашу подписку."
                              f"\n**Ваш платеж может быть подтвержден с задержкой, ожидайте, пожалуйста.**",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown')
        
        # Уведомляем админа о новом платеже
        bot.send_message(ADMIN_ID, 
                         f"🔔 Новый платеж на {amount_to_transfer} ₽ (общая сумма {total_amount} ₽, с баланса {balance_used} ₽) "
                         f"от @{call.from_user.username} (ID: {user_id}) за {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}. "
                         f"Ожидает скриншот.", 
                         reply_markup=main_menu_keyboard(ADMIN_ID))

    # --- Оплата Telegram Stars (полная или доплата) ---
    elif call.data.startswith("pay_stars_"):
        parts = call.data.split('_')
        period_data = f"{parts[2]}_{parts[3]}"
        total_amount = int(parts[4])
        balance_used = int(parts[5]) if len(parts) > 5 else 0 # Сколько было использовано с баланса
        
        amount_to_pay_stars = total_amount - balance_used
        
        # Списываем баланс сразу, если он использовался для частичной оплаты
        if balance_used > 0:
            users_db[user_id]['balance'] -= balance_used
            save_data('users.json', users_db)

        # Конвертируем в Stars (1 звезда = 1.5 рубля)
        stars_amount = int(amount_to_pay_stars / STARS_TO_RUB)
        
        # Создаем инвойс для оплаты Stars
        try:
            prices = [types.LabeledPrice(label=f"VPN подписка на {period_data.replace('_', ' ')}", amount=stars_amount)]  # В звездах
            
            # Сохраняем информацию о платеже Stars (pending) до успешной оплаты
            payment_id = generate_payment_id()
            payments_db[payment_id] = {
                'user_id': user_id,
                'amount': total_amount,
                'status': 'pending_stars', # Специальный статус для ожидания подтверждения Stars
                'screenshot_id': None,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period': period_data,
                'method': 'stars',
                'balance_used': balance_used,
                'stars_payload': f'vpn_subscription_{period_data}_{user_id}_{payment_id}' # Добавляем payment_id в payload
            }
            save_data('payments.json', payments_db)

            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"VPN подписка на {period_data.replace('_', ' ')}",
                description=f"VPN подписка на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}",
                provider_token='',  # Для Stars не нужен provider_token
                currency='XTR',  # Код валюты для Telegram Stars
                prices=prices,
                start_parameter=f'vpn_subscription_{period_data}',
                invoice_payload=payments_db[payment_id]['stars_payload']
            )
        except Exception as e:
            bot.edit_message_text(f"Ошибка при создании платежа Stars: {e}\nПожалуйста, используйте оплату картой.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id)

    # --- ЛИЧНЫЙ КАБИНЕТ ---
    elif call.data == "my_account":
        user_info = users_db.get(user_id, {})
        subscription_end = user_info.get('subscription_end')
        balance = user_info.get('balance', 0)

        status_text = "Нет активной подписки"
        remaining_days = 0
        if subscription_end:
            end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
            if end_date > datetime.datetime.now():
                delta = end_date - datetime.datetime.now()
                remaining_days = delta.days
                status_text = f"Подписка активна до: {end_date.strftime('%d.%m.%Y %H:%M')} (Осталось: {remaining_days} дн.)"
            else:
                status_text = "Подписка истекла"
                users_db[user_id]['subscription_end'] = None # Обнуляем, если истекла
                # Деактивируем выданные конфиги
                for cfg in users_db[user_id].get('used_configs', []):
                    cfg['is_active'] = False
                save_data('users.json', users_db)

        bot.edit_message_text(f"👤 Ваш личный кабинет:\n\n"
                              f"Статус подписки: {status_text}\n"
                              f"Баланс: {balance} ₽\n"
                              f"Ваше имя: {user_info.get('first_name', 'N/A')}\n"
                              f"Ваш username: @{user_info.get('username', 'N/A')}\n\n",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=my_account_keyboard())

    elif call.data == "my_configs":
        bot.edit_message_text("Выберите конфиг для получения:",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=my_configs_keyboard(user_id))

    elif call.data.startswith("show_my_config_"):
        period_data = call.data.replace("show_my_config_", "")
        user_info = users_db.get(user_id, {})
        
        # Проверяем активную подписку
        subscription_end = user_info.get('subscription_end')
        if not subscription_end:
            bot.send_message(call.message.chat.id, "❌ У вас нет активной подписки.")
            return
        
        end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
        if end_date <= datetime.datetime.now():
            bot.send_message(call.message.chat.id, "❌ Ваша подписка истекла.")
            return
        
        # Ищем уже выданный конфиг
        found_config = None
        for cfg in user_info.get('used_configs', []):
            if cfg['period'] == period_data and cfg.get('is_active', True):
                found_config = cfg
                break
        
        if found_config:
            bot.send_message(user_id, f"🔐 **Ваш VPN конфиг**\n\n"
                                     f"👤 **Имя:** {found_config['config_name']}\n"
                                     f"📅 **Период:** {found_config['period'].replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}\n"
                                     f"🔗 **Ссылка на конфиг:** {found_config['config_link']}\n\n"
                                     f"💾 _Сохраните этот конфиг для использования_",
                             parse_mode='Markdown')
            bot.answer_callback_query(call.id, "Конфиг отправлен вам в личные сообщения.")
        else:
            bot.send_message(call.message.chat.id, "❌ Конфиг для этого периода не найден или неактивен. Возможно, подписка истекла или конфиг был удален администратором.")

    # --- ПОДДЕРЖКА ---
    elif call.data == "support":
        bot.edit_message_text(f"Для связи с поддержкой напишите {ADMIN_USERNAME}.\n"
                              f"Постараемся ответить как можно скорее.",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=main_menu_keyboard(user_id))

    # --- РЕФЕРАЛЬНАЯ СИСТЕМА ---
    elif call.data == "referral_system":
        referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        user_info = users_db.get(user_id, {})
        referrals_count = user_info.get('referrals_count', 0)
        balance = user_info.get('balance', 0)

        bot.edit_message_text(f"🤝 **Реферальная система**\n\n"
                              f"💡 **Как это работает:**\n"
                              f"• Вы получаете уникальную реферальную ссылку\n"
                              f"• Делитесь ей с друзьями и знакомыми\n"
                              f"• Когда кто-то регистрируется по вашей ссылке:\n"
                              f"  🔹 Новый пользователь получает {REFERRAL_BONUS_NEW_USER_RUB} ₽ на баланс.\n"
                              f"• Когда реферал совершает **первую покупку** подписки:\n"
                              f"  🔹 Вы получаете {REFERRAL_BONUS_INVITER_RUB} ₽ на баланс\n"
                              f"  🔹 И {REFERRAL_BONUS_INVITER_DAYS} дней к вашей активной подписке\n\n"
                              f"💰 **Ваши бонусы:**\n"
                              f"• Рефералов приглашено (с первой покупкой): {referrals_count}\n"
                              f"• Реферальный баланс: {balance} ₽\n\n"
                              f"📎 **Ваша реферальная ссылка:**\n"
                              f"`{referral_link}`\n\n"
                              f"💸 Баланс можно использовать для оплаты подписки!",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown', reply_markup=main_menu_keyboard(user_id))

    # --- АДМИН-ПАНЕЛЬ ---
    elif call.data == "admin_panel":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("🛠️ Админ-панель:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
            bot.edit_message_text("Главное меню:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=main_menu_keyboard(user_id))

    elif call.data == "admin_manage_configs":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Управление конфигами:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=manage_configs_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_show_configs":
        if str(user_id) == str(ADMIN_ID):
            message_text = "**Текущие конфиги:**\n\n"
            for period, configs_list in configs_db.items():
                message_text += f"**{period.replace('_', ' ').capitalize()}:**\n"
                if configs_list:
                    for i, config in enumerate(configs_list):
                        status = "✅ Свободен" if not config.get('is_used', False) else "❌ Использован"
                        message_text += f"  {i+1}. Имя: {config['name']}, Код: `{config['code']}`, Статус: {status} (ID: {i})\n"
                else:
                    message_text += "  (Нет конфигов)\n"
            
            bot.edit_message_text(message_text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown', reply_markup=manage_configs_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_add_config":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Выберите период подписки для конфига:", 
                                 chat_id=call.message.chat.id, message_id=call.message.message_id,
                                 reply_markup=choose_period_keyboard("add_config"))
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("add_config_"):
        if str(user_id) == str(ADMIN_ID):
            period = call.data.replace("add_config_", "")
            bot.edit_message_text(f"Добавление конфигов для периода: {period.replace('_', ' ')}\n\n"
                                 f"Отправьте ссылки на конфиги, каждую с новой строки.",
                                 chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_add_configs_bulk, period)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_delete_config":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите период и ID конфига для удаления (например, `1_month 0` для первого конфига на 1 месяц).")
            bot.register_next_step_handler(call.message, process_delete_config)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_delete_all_configs": # Обработка новой кнопки
        if str(user_id) == str(ADMIN_ID):
            confirm_markup = types.InlineKeyboardMarkup(row_width=2)
            confirm_markup.add(
                types.InlineKeyboardButton("Да, удалить все", callback_data="admin_confirm_delete_all_configs"),
                types.InlineKeyboardButton("Отмена", callback_data="admin_manage_configs")
            )
            bot.edit_message_text("Вы уверены, что хотите удалить ВСЕ конфиги для ВСЕХ периодов? Это действие необратимо!",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=confirm_markup)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_confirm_delete_all_configs":
        if str(user_id) == str(ADMIN_ID):
            global configs_db
            configs_db = {'1_month': [], '2_months': [], '3_months': []}
            save_data('configs.json', configs_db)
            
            # Также очищаем использованные конфиги у пользователей и помечаем их подписки как неактивные
            for uid in users_db:
                users_db[uid]['used_configs'] = []
                # users_db[uid]['subscription_end'] = None # Не удаляем подписку, только конфиги
            save_data('users.json', users_db)

            bot.edit_message_text("✅ Все конфиги успешно удалены и сведения об использованных конфигах пользователей очищены.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")


    elif call.data == "admin_confirm_payments":
        if str(user_id) == str(ADMIN_ID):
            pending_payments = {pid: p_data for pid, p_data in payments_db.items() if p_data['status'] == 'pending' and p_data['screenshot_id']}
            if not pending_payments:
                bot.edit_message_text("Нет платежей, ожидающих подтверждения со скриншотами.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_keyboard())
                return
            
            for payment_id, p_data in pending_payments.items():
                user_payment_info = users_db.get(p_data['user_id'])
                if user_payment_info:
                    amount_to_transfer = p_data.get('amount_to_transfer', p_data['amount'])
                    balance_used_info = f" (с баланса {p_data.get('balance_used', 0)} ₽)" if p_data.get('balance_used', 0) > 0 else ""
                    
                    bot.send_photo(ADMIN_ID, p_data['screenshot_id'], 
                                   caption=f"Платеж ID: {payment_id}\n"
                                           f"От: @{user_payment_info.get('username', 'N/A')} (ID: {p_data['user_id']})\n"
                                           f"Сумма перевода: {amount_to_transfer} ₽\n"
                                           f"Общая сумма: {p_data['amount']} ₽{balance_used_info}\n"
                                           f"Период: {p_data['period'].replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}\n"
                                           f"Время: {p_data['timestamp']}",
                                   reply_markup=confirm_payments_keyboard(payment_id))
            bot.send_message(ADMIN_ID, "👆 Это все платежи со скриншотами, ожидающие подтверждения.", reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_confirm_"):
        if str(user_id) == str(ADMIN_ID):
            payment_id = call.data.replace("admin_confirm_", "")
            if payment_id in payments_db and payments_db[payment_id]['status'] == 'pending':
                payments_db[payment_id]['status'] = 'confirmed'
                
                target_user_id = payments_db[payment_id]['user_id']
                period_data = payments_db[payment_id]['period']
                balance_used_for_payment = payments_db[payment_id].get('balance_used', 0)

                # Обновляем подписку пользователя
                update_user_subscription(target_user_id, period_data)

                # Отмечаем первую покупку для реферальной системы
                if not users_db[target_user_id].get('first_purchase_made', False):
                    users_db[target_user_id]['first_purchase_made'] = True
                    # Начисляем бонус рефереру
                    referrer_id = users_db[target_user_id].get('referred_by')
                    if referrer_id and referrer_id in users_db:
                        users_db[referrer_id]['referrals_count'] = users_db[referrer_id].get('referrals_count', 0) + 1
                        users_db[referrer_id]['balance'] = users_db[referrer_id].get('balance', 0) + REFERRAL_BONUS_INVITER_RUB
                        
                        # Добавляем дни подписки рефереру, если у него есть активная подписка
                        if users_db[referrer_id].get('subscription_end'):
                            current_end_ref = datetime.datetime.strptime(users_db[referrer_id]['subscription_end'], '%Y-%m-%d %H:%M:%S')
                            new_end_ref = current_end_ref + datetime.timedelta(days=REFERRAL_BONUS_INVITER_DAYS)
                            users_db[referrer_id]['subscription_end'] = new_end_ref.strftime('%Y-%m-%d %H:%M:%S')
                            bot.send_message(referrer_id, 
                                            f"🎉 Ваш реферал @{users_db[target_user_id].get('username', 'N/A')} совершил первую покупку! "
                                            f"Вам начислено {REFERRAL_BONUS_INVITER_RUB} ₽ на баланс и {REFERRAL_BONUS_INVITER_DAYS} дней к подписке!")
                        else:
                            bot.send_message(referrer_id, 
                                            f"🎉 Ваш реферал @{users_db[target_user_id].get('username', 'N/A')} совершил первую покупку! "
                                            f"Вам начислено {REFERRAL_BONUS_INVITER_RUB} ₽ на баланс.")
                save_data('users.json', users_db)

                # Выдаем конфиг после подтверждения платежа
                issue_config_and_notify_user(target_user_id, period_data)
                
                save_data('payments.json', payments_db)
                bot.edit_message_text(f"Платеж {payment_id} подтвержден.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            else:
                bot.edit_message_text("Платеж уже обработан или не найден.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_reject_"):
        if str(user_id) == str(ADMIN_ID):
            payment_id = call.data.replace("admin_reject_", "")
            if payment_id in payments_db and payments_db[payment_id]['status'] == 'pending':
                # Возвращаем использованный баланс, если платеж отклонен
                balance_returned = payments_db[payment_id].get('balance_used', 0)
                if balance_returned > 0:
                    users_db[payments_db[payment_id]['user_id']]['balance'] += balance_returned
                    save_data('users.json', users_db)
                    bot.send_message(payments_db[payment_id]['user_id'], f"💰 {balance_returned} ₽ возвращены на ваш баланс, так как платеж был отклонен.")

                payments_db[payment_id]['status'] = 'rejected'
                save_data('payments.json', payments_db)
                
                target_user_id = payments_db[payment_id]['user_id']
                bot.send_message(target_user_id, 
                                 f"❌ Ваш платеж (ID: {payment_id}) был отклонен администратором. "
                                 f"Пожалуйста, свяжитесь с поддержкой ({ADMIN_USERNAME}) для уточнения.",
                                 reply_markup=main_menu_keyboard(target_user_id))
                
                bot.edit_message_text(f"Платеж {payment_id} отклонен.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            else:
                bot.edit_message_text("Платеж уже обработан или не найден.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_users_list":
        if str(user_id) == str(ADMIN_ID):
            message_text = "**Список пользователей:**\n\n"
            for uid, u_data in users_db.items():
                sub_end_str = "Нет"
                remaining_days = "N/A"
                if u_data.get('subscription_end'):
                    sub_end = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                    if sub_end > datetime.datetime.now():
                        delta = sub_end - datetime.datetime.now()
                        remaining_days = delta.days
                        sub_end_str = sub_end.strftime('%d.%m.%Y %H:%M') + f" ({remaining_days} дн.)"
                    else:
                        sub_end_str = "Истекла"
                
                message_text += f"ID: {uid}\n" \
                                f"  Имя: {u_data.get('first_name', 'N/A')} (@{u_data.get('username', 'N/A')})\n" \
                                f"  Подписка до: {sub_end_str}\n" \
                                f"  Баланс: {u_data.get('balance', 0)} ₽\n" \
                                f"  Рефералов: {u_data.get('referrals_count', 0)}\n\n"
            
            bot.edit_message_text(message_text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown', reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_manage_users":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Управление пользователями:", 
                                 chat_id=call.message.chat.id, message_id=call.message.message_id,
                                 reply_markup=users_management_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_active_users":
        if str(user_id) == str(ADMIN_ID):
            message_text = "**Активные пользователи (с подпиской):**\n\n"
            active_count = 0
            
            for uid, u_data in users_db.items():
                if u_data.get('subscription_end'):
                    sub_end = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                    if sub_end > datetime.datetime.now():
                        active_count += 1
                        referred_by = "Нет"
                        if u_data.get('referred_by'):
                            referrer = users_db.get(u_data['referred_by'], {})
                            referred_by = f"@{referrer.get('username', 'N/A')} (ID: {u_data['referred_by']})"
                        
                        delta = sub_end - datetime.datetime.now()
                        remaining_days = delta.days

                        message_text += f"👤 **{u_data.get('first_name', 'N/A')}** (@{u_data.get('username', 'N/A')})\n"
                        message_text += f"🆔 ID: `{uid}`\n"
                        message_text += f"💰 Баланс: {u_data.get('balance', 0)} ₽\n"
                        message_text += f"📅 Подписка до: {sub_end.strftime('%d.%m.%Y %H:%M')} ({remaining_days} дн.)\n"
                        message_text += f"🤝 Рефералов: {u_data.get('referrals_count', 0)}\n"
                        message_text += f"📎 Приглашен: {referred_by}\n"
                        message_text += f"⚡ Действия: /manage_{uid}\n\n"
            
            if active_count == 0:
                message_text = "❌ Нет активных пользователей."
            
            bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_all_users":
        if str(user_id) == str(ADMIN_ID):
            message_text = f"**Все пользователи ({len(users_db)}):**\n\n"
            
            for i, (uid, u_data) in enumerate(users_db.items(), 1):
                sub_status = "❌ Нет подписки"
                if u_data.get('subscription_end'):
                    sub_end = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                    if sub_end > datetime.datetime.now():
                        delta = sub_end - datetime.datetime.now()
                        sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y')} ({delta.days} дн.)"
                    else:
                        sub_status = "❌ Истекла"
                
                message_text += f"{i}. **{u_data.get('first_name', 'N/A')}** (@{u_data.get('username', 'N/A')})\n"
                message_text += f"   🆔: `{uid}` | {sub_status}\n"
                message_text += f"   💰: {u_data.get('balance', 0)} ₽ | 🤝: {u_data.get('referrals_count', 0)}\n"
                message_text += f"   ⚡ /manage_{uid}\n\n"
            
            bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_search_user":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите username или ID пользователя для поиска:")
            bot.register_next_step_handler(call.message, process_search_user)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_edit_user":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите ID пользователя, которого хотите изменить:")
            bot.register_next_step_handler(call.message, process_edit_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_edit_balance_"):
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_edit_balance_", "")
            bot.send_message(call.message.chat.id, f"Введите новый баланс для пользователя {target_user_id}:")
            bot.register_next_step_handler(call.message, process_edit_balance, target_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_edit_subscription_"):
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_edit_subscription_", "")
            bot.send_message(call.message.chat.id, f"Введите новую дату окончания подписки для пользователя {target_user_id} (формат: ДД.ММ.ГГГГ ЧЧ:ММ или 'нет' для удаления):")
            bot.register_next_step_handler(call.message, process_edit_subscription, target_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_view_user_configs_"):
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_view_user_configs_", "")
            user_info = users_db.get(target_user_id, {})
            used_configs = user_info.get('used_configs', [])
            
            if used_configs:
                message_text = f"**Конфиги пользователя {user_info.get('first_name', 'N/A')} (@{user_info.get('username', 'N/A')}):**\n\n"
                for i, config in enumerate(used_configs, 1):
                    status = "✅ Активен" if config.get('is_active', True) else "❌ Неактивен"
                    message_text += f"{i}. **{config['config_name']}** ({status})\n"
                    message_text += f"   Период: {config['period']}\n"
                    message_text += f"   Выдан: {config['issue_date']}\n"
                    message_text += f"   Ссылка: {config['config_link']}\n\n"
            else:
                message_text = "❌ У пользователя нет выданных конфигов."
            
            bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_manage_user_configs":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Управление конфигами пользователей:",
                                 chat_id=call.message.chat.id, message_id=call.message.message_id,
                                 reply_markup=user_configs_management_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_show_user_configs":
        if str(user_id) == str(ADMIN_ID):
            message_text = "**Все выданные конфиги:**\n\n"
            config_count = 0
            
            for uid, user_data in users_db.items():
                used_configs = user_data.get('used_configs', [])
                if used_configs:
                    message_text += f"👤 **Пользователь:** {user_data.get('first_name', 'N/A')} (@{user_data.get('username', 'N/A')}) ID: {uid}\n"
                    for i, config in enumerate(used_configs):
                        config_count += 1
                        status = "✅ Активен" if config.get('is_active', True) else "❌ Неактивен"
                        message_text += f"  {i+1}. {config['config_name']} ({config['period']}) - {status}\n"
                        message_text += f"     Ссылка: {config['config_link']}\n"
                        message_text += f"     Выдан: {config['issue_date']}\n\n"
            
            if config_count == 0:
                message_text = "❌ Нет выданных конфигов."
            
            bot.send_message(call.message.chat.id, message_text, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_delete_user_config":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите ID пользователя и номер конфига для удаления (например, `123456789 1`):")
            bot.register_next_step_handler(call.message, process_delete_user_config)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_reissue_config":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите ID пользователя для перевыдачи конфига:")
            bot.register_next_step_handler(call.message, process_reissue_config)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_broadcast":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите сообщение для рассылки всем пользователям:")
            bot.register_next_step_handler(call.message, process_broadcast_message)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

# --- Вспомогательные функции для обновления подписки и выдачи конфига ---
def update_user_subscription(user_id, period_data):
    if user_id in users_db:
        current_end = users_db[user_id].get('subscription_end')
        if current_end:
            current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
        else:
            current_end = datetime.datetime.now()

        add_days = 0
        if period_data == '1_month': add_days = 30
        elif period_data == '2_months': add_days = 60
        elif period_data == '3_months': add_days = 90
        
        new_end = current_end + datetime.timedelta(days=add_days)
        users_db[user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
        # Активируем все конфиги пользователя (если были неактивны)
        for cfg in users_db[user_id].get('used_configs', []):
            cfg['is_active'] = True
        save_data('users.json', users_db)
        return new_end
    return None

def issue_config_and_notify_user(user_id, period_data):
    user_info = users_db[user_id]
    new_end_date = datetime.datetime.strptime(user_info['subscription_end'], '%Y-%m-%d %H:%M:%S')

    success, result = get_or_send_config_to_user(user_id, period_data, 
                                                user_info.get('username', 'user'), 
                                                user_info.get('first_name', 'User'))
    
    if success:
        bot.send_message(user_id, 
                         f"✅ Ваша подписка на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')} подтверждена!\n"
                         f"Ваша подписка активна до: {new_end_date.strftime('%d.%m.%Y %H:%M')}\n"
                         f"Конфиг уже выдан! Проверьте сообщения выше.",
                         reply_markup=main_menu_keyboard(user_id))
    else:
        bot.send_message(user_id, 
                         f"✅ Платеж подтвержден, но возникла ошибка при выдаче конфига: {result}\n"
                         f"Обратитесь в поддержку: {ADMIN_USERNAME}")

def notify_admin_of_successful_payment(user_id, total_amount, period_data, method, balance_used=0):
    user_info = users_db[user_id]
    balance_used_info = f" (с баланса {balance_used} ₽)" if balance_used > 0 else ""
    bot.send_message(ADMIN_ID, 
                     f"✅ Успешная оплата {method} на {total_amount} ₽{balance_used_info}\n"
                     f"От: @{user_info.get('username', 'N/A')} (ID: {user_id})\n"
                     f"Период: {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}")


# --- ОБРАБОТЧИК КОМАНД ---
@bot.message_handler(commands=['manage'])
def handle_manage_command(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        user_id = message.text.split('_')[1]
        if user_id in users_db:
            user_info = users_db[user_id]
            sub_status = "❌ Нет подписки"
            if user_info.get('subscription_end'):
                sub_end = datetime.datetime.strptime(user_info['subscription_end'], '%Y-%m-%d %H:%M:%S')
                if sub_end > datetime.datetime.now():
                    delta = sub_end - datetime.datetime.now()
                    sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y %H:%M')} ({delta.days} дн.)"
                else:
                    sub_status = "❌ Истекла"
            
            message_text = f"👤 **Управление пользователем:**\n\n"
            message_text += f"**Имя:** {user_info.get('first_name', 'N/A')}\n"
            message_text += f"**Username:** @{user_info.get('username', 'N/A')}\n"
            message_text += f"**ID:** `{user_id}`\n"
            message_text += f"**Баланс:** {user_info.get('balance', 0)} ₽\n"
            message_text += f"**Подписка:** {sub_status}\n"
            message_text += f"**Рефералов:** {user_info.get('referrals_count', 0)}\n"
            message_text += f"**Конфигов выдано:** {len(user_info.get('used_configs', []))}\n"
            
            bot.send_message(message.chat.id, message_text, 
                           reply_markup=user_action_keyboard(user_id),
                           parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
    except IndexError:
        bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /manage_USER_ID")

# --- ОБРАБОТЧИК ПРЕДОПЛАТЫ (Telegram Stars) ---
@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    # Дополнительная проверка на наличие платежа в статусе 'pending_stars'
    # Используем invoice_payload для поиска соответствующего платежа
    payload_parts = pre_checkout_query.invoice_payload.split('_')
    if len(payload_parts) >= 5: # vpn_subscription_{period_data}_{user_id}_{payment_id}
        payment_id_from_payload = payload_parts[4]
        if payment_id_from_payload in payments_db and payments_db[payment_id_from_payload]['status'] == 'pending_stars':
            bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
            return
    
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="Платеж Stars не найден или истек. Пожалуйста, попробуйте снова.")


@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    user_id = str(message.from_user.id)
    payment_info = message.successful_payment
    
    # Извлекаем payment_id из invoice_payload
    payload_parts = payment_info.invoice_payload.split('_')
    if len(payload_parts) >= 5: # vpn_subscription_{period_data}_{user_id}_{payment_id}
        payment_id_from_payload = payload_parts[4]
        
        if payment_id_from_payload in payments_db and payments_db[payment_id_from_payload]['status'] == 'pending_stars':
            payment_record = payments_db[payment_id_from_payload]
            payment_record['status'] = 'confirmed'
            # Stars amount from Telegram is in smallest units, so amount is already correct.
            # Convert back to rubles for internal tracking if needed, or keep in Stars for clarity.
            # We store 'amount' as total rubles, 'balance_used' as rubles, so 'amount_to_transfer' is the Stars equivalent in rubles.
            payment_record['amount_to_transfer'] = payment_info.total_amount * STARS_TO_RUB # Сумма, оплаченная Stars, в рублях
            
            period_data = payment_record['period']
            total_amount = payment_record['amount']
            balance_used = payment_record['balance_used']

            save_data('payments.json', payments_db)
            
            # Обновляем подписку пользователя
            update_user_subscription(user_id, period_data)

            # Отмечаем первую покупку для реферальной системы
            if not users_db[user_id].get('first_purchase_made', False):
                users_db[user_id]['first_purchase_made'] = True
                referrer_id = users_db[user_id].get('referred_by')
                if referrer_id and referrer_id in users_db:
                    users_db[referrer_id]['referrals_count'] = users_db[referrer_id].get('referrals_count', 0) + 1
                    users_db[referrer_id]['balance'] = users_db[referrer_id].get('balance', 0) + REFERRAL_BONUS_INVITER_RUB
                    if users_db[referrer_id].get('subscription_end'):
                        current_end_ref = datetime.datetime.strptime(users_db[referrer_id]['subscription_end'], '%Y-%m-%d %H:%M:%S')
                        new_end_ref = current_end_ref + datetime.timedelta(days=REFERRAL_BONUS_INVITER_DAYS)
                        users_db[referrer_id]['subscription_end'] = new_end_ref.strftime('%Y-%m-%d %H:%M:%S')
                        bot.send_message(referrer_id, 
                                        f"🎉 Ваш реферал @{message.from_user.username} совершил первую покупку! "
                                        f"Вам начислено {REFERRAL_BONUS_INVITER_RUB} ₽ на баланс и {REFERRAL_BONUS_INVITER_DAYS} дней к подписке!")
                    else:
                        bot.send_message(referrer_id, 
                                        f"🎉 Ваш реферал @{message.from_user.username} совершил первую покупку! "
                                        f"Вам начислено {REFERRAL_BONUS_INVITER_RUB} ₽ на баланс.")
            save_data('users.json', users_db)

            # Выдаем конфиг
            issue_config_and_notify_user(user_id, period_data)
            
            # Уведомляем админа
            notify_admin_of_successful_payment(user_id, total_amount, period_data, 'Telegram Stars', balance_used)
        else:
            bot.send_message(user_id, "❌ Произошла ошибка при обработке платежа Stars. Пожалуйста, свяжитесь с поддержкой.")

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = str(message.from_user.id)
    # Ищем ожидающий платеж от этого пользователя
    pending_payment = None
    for payment_id, p_data in payments_db.items():
        if p_data['user_id'] == user_id and p_data['status'] == 'pending' and p_data['screenshot_id'] is None:
            pending_payment = payment_id
            break
    
    if pending_payment:
        payments_db[pending_payment]['screenshot_id'] = message.photo[-1].file_id
        save_data('payments.json', payments_db)
        
        bot.send_message(message.chat.id, "Скриншот получен! Ожидайте подтверждения от администратора. "
                                         "Ваш платеж может быть подтвержден с задержкой.")
        
        # Уведомляем админа о новом скриншоте
        amount_to_transfer = payments_db[pending_payment].get('amount_to_transfer', payments_db[pending_payment]['amount'])
        balance_used_info = f" (с баланса {payments_db[pending_payment].get('balance_used', 0)} ₽)" if payments_db[pending_payment].get('balance_used', 0) > 0 else ""

        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                       caption=f"❗️ Новый скриншот платежа ID: {pending_payment}\n"
                               f"От: @{message.from_user.username} (ID: {user_id})\n"
                               f"Сумма перевода: {amount_to_transfer} ₽\n"
                               f"Общая сумма: {payments_db[pending_payment]['amount']} ₽{balance_used_info}\n"
                               f"Период: {payments_db[pending_payment]['period'].replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}",
                       reply_markup=confirm_payments_keyboard(pending_payment))

# --- ФУНКЦИИ АДМИНКИ (продолжение) ---
def process_add_configs_bulk(message, period):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    if period not in configs_db:
        configs_db[period] = []
    
    links = message.text.strip().split('\n')
    added_count = 0
    
    for link in links:
        link = link.strip()
        if link and link.startswith(('http://', 'https://')):
            # Генерируем имя на основе username администратора
            username = message.from_user.username if message.from_user.username else 'admin'
            config_name = f"Config_{period}_{len(configs_db[period]) + 1}"
            
            config_data = {
                'name': config_name,
                'image': None,
                'code': f"{period}_{len(configs_db[period]) + 1}_{datetime.datetime.now().strftime('%H%M%S')}",
                'link': link,
                'added_by': username,
                'is_used': False # Новый конфиг по умолчанию не использован
            }
            
            configs_db[period].append(config_data)
            added_count += 1
    
    save_data('configs.json', configs_db)
    bot.send_message(message.chat.id, f"✅ Добавлено {added_count} конфигов для периода {period.replace('_', ' ')}.", 
                     reply_markup=manage_configs_keyboard())

def process_delete_config(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        parts = message.text.strip().split()
        period = parts[0]
        config_id = int(parts[1])
        
        if period in configs_db and 0 <= config_id < len(configs_db[period]):
            deleted_config = configs_db[period].pop(config_id)
            save_data('configs.json', configs_db)
            bot.send_message(message.chat.id, f"✅ Конфиг '{deleted_config['name']}' удален из периода {period}.")
        else:
            bot.send_message(message.chat.id, "❌ Неверный период или ID конфига.")
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: `период ID` (например, `1_month 0`)", parse_mode='Markdown')

def process_search_user(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    search_term = message.text.strip()
    found_users = []
    
    # Поиск по username (без @)
    if search_term.startswith('@'):
        search_term = search_term[1:]
    
    for uid, user_data in users_db.items():
        if (search_term.lower() in user_data.get('username', '').lower() or 
            search_term == uid or
            search_term.lower() in user_data.get('first_name', '').lower()):
            found_users.append((uid, user_data))
    
    if found_users:
        message_text = f"**Найдено пользователей: {len(found_users)}**\n\n"
        for uid, user_data in found_users:
            sub_status = "❌ Нет подписки"
            if user_data.get('subscription_end'):
                sub_end = datetime.datetime.strptime(user_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                if sub_end > datetime.datetime.now():
                    delta = sub_end - datetime.datetime.now()
                    sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y')} ({delta.days} дн.)"
                else:
                    sub_status = "❌ Истекла"
            
            message_text += f"👤 **{user_data.get('first_name', 'N/A')}** (@{user_data.get('username', 'N/A')})\n"
            message_text += f"🆔 ID: `{uid}`\n"
            message_text += f"📊 {sub_status} | 💰 {user_data.get('balance', 0)} ₽\n"
            message_text += f"⚡ /manage_{uid}\n\n"
        
        bot.send_message(message.chat.id, message_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Пользователи не найдены.")

def process_edit_user_id(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    target_user_id = message.text.strip()
    if target_user_id in users_db:
        user_info = users_db[target_user_id]
        sub_status = "❌ Нет подписки"
        if user_info.get('subscription_end'):
            sub_end = datetime.datetime.strptime(user_info['subscription_end'], '%Y-%m-%d %H:%M:%S')
            if sub_end > datetime.datetime.now():
                delta = sub_end - datetime.datetime.now()
                sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y %H:%M')} ({delta.days} дн.)"
            else:
                sub_status = "❌ Истекла"
        
        message_text = f"👤 **Редактирование пользователя:**\n\n"
        message_text += f"**Имя:** {user_info.get('first_name', 'N/A')}\n"
        message_text += f"**Username:** @{user_info.get('username', 'N/A')}\n"
        message_text += f"**ID:** `{target_user_id}`\n"
        message_text += f"**Баланс:** {user_info.get('balance', 0)} ₽\n"
        message_text += f"**Подписка:** {sub_status}\n"
        
        bot.send_message(message.chat.id, message_text, 
                       reply_markup=user_action_keyboard(target_user_id),
                       parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Пользователь не найден.")

def process_edit_balance(message, target_user_id):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        new_balance = int(message.text.strip())
        old_balance = users_db[target_user_id].get('balance', 0)
        users_db[target_user_id]['balance'] = new_balance
        save_data('users.json', users_db)
        
        bot.send_message(message.chat.id, 
                        f"✅ Баланс пользователя {target_user_id} изменен:\n"
                        f"С {old_balance} ₽ на {new_balance} ₽")
        
        # Уведомляем пользователя
        bot.send_message(target_user_id, 
                        f"💰 Администратор изменил ваш баланс.\n"
                        f"Новый баланс: {new_balance} ₽")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат баланса. Введите число.")

def process_edit_subscription(message, target_user_id):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    new_subscription = message.text.strip()
    if new_subscription.lower() == 'нет':
        old_subscription = users_db[target_user_id].get('subscription_end')
        users_db[target_user_id]['subscription_end'] = None
        # Деактивируем все выданные конфиги пользователя
        for cfg in users_db[target_user_id].get('used_configs', []):
            cfg['is_active'] = False
        save_data('users.json', users_db)
        
        bot.send_message(message.chat.id, f"✅ Подписка пользователя {target_user_id} удалена.")
        bot.send_message(target_user_id, "❌ Ваша подписка была удалена администратором.")
    else:
        try:
            new_end = datetime.datetime.strptime(new_subscription, '%d.%m.%Y %H:%M')
            users_db[target_user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            # Активируем все конфиги пользователя (если были неактивны)
            for cfg in users_db[target_user_id].get('used_configs', []):
                cfg['is_active'] = True
            save_data('users.json', users_db)
            
            bot.send_message(message.chat.id, 
                            f"✅ Подписка пользователя {target_user_id} установлена до {new_end.strftime('%d.%m.%Y %H:%M')}.")
            bot.send_message(target_user_id, 
                            f"✅ Администратор изменил срок вашей подписки.\n"
                            f"Новая дата окончания: {new_end.strftime('%d.%m.%Y %H:%M')}")
        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверный формат даты. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")

def process_delete_user_config(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        parts = message.text.strip().split()
        user_id = parts[0]
        config_index = int(parts[1]) - 1  # -1 потому что пользователь вводит начиная с 1
        
        if user_id in users_db:
            used_configs = users_db[user_id].get('used_configs', [])
            if 0 <= config_index < len(used_configs):
                deleted_config = used_configs.pop(config_index)
                
                # Помечаем конфиг как свободный в общей базе, если он был там
                for period_key in configs_db:
                    for cfg in configs_db[period_key]:
                        if cfg['code'] == deleted_config['config_code']:
                            cfg['is_used'] = False
                            break
                
                users_db[user_id]['used_configs'] = used_configs
                save_data('users.json', users_db)
                save_data('configs.json', configs_db) # Сохраняем изменение статуса конфига
                
                bot.send_message(message.chat.id, 
                                f"✅ Конфиг пользователя {user_id} удален:\n"
                                f"Имя: {deleted_config['config_name']}\n"
                                f"Период: {deleted_config['period']}")
                
                # Уведомляем пользователя
                bot.send_message(user_id, 
                                f"❌ Ваш конфиг '{deleted_config['config_name']}' был удален администратором.")
            else:
                bot.send_message(message.chat.id, "❌ Неверный номер конфига.")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: `ID_пользователя номер_конфига`")

def process_reissue_config(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        user_id = message.text.strip()
        if user_id in users_db:
            user_info = users_db[user_id]
            bot.send_message(message.chat.id, 
                            f"Пользователь: {user_info.get('first_name', 'N/A')} (@{user_info.get('username', 'N/A')})\n"
                            f"Введите период для перевыдачи конфига (1_month, 2_months, 3_months):")
            bot.register_next_step_handler(message, process_reissue_period, user_id)
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

def process_reissue_period(message, user_id):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    period = message.text.strip()
    if period in ['1_month', '2_months', '3_months']:
        user_info = users_db[user_id]
        
        # Сначала удаляем все старые конфиги этого периода у пользователя
        users_db[user_id]['used_configs'] = [
            cfg for cfg in users_db[user_id].get('used_configs', []) if cfg['period'] != period
        ]
        save_data('users.json', users_db)

        success, result = get_or_send_config_to_user(user_id, period, 
                                                    user_info.get('username', 'user'), 
                                                    user_info.get('first_name', 'User'))
        
        if success:
            bot.send_message(message.chat.id, f"✅ Конфиг успешно перевыдан пользователю {user_id}")
            bot.send_message(user_id, f"✅ Администратор перевыдал вам конфиг на период {period.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}. Проверьте сообщения выше.")
        else:
            bot.send_message(message.chat.id, f"❌ Ошибка при перевыдаче: {result}")
    else:
        bot.send_message(message.chat.id, "❌ Неверный период. Используйте: 1_month, 2_months, 3_months")

def process_broadcast_message(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    broadcast_text = message.text
    sent_count
