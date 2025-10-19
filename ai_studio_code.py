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

REFERRAL_BONUS_NEW_USER = 50 # Рублей новому пользователю
REFERRAL_BONUS_REFERRER = 25 # Рублей тому кто пригласил
REFERRAL_BONUS_DAYS = 7 # Дней подписки за реферала

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

# --- ОЧИСТКА КОНФИГОВ ПРИ ПЕРВОМ ЗАПУСКЕ ---
def reset_configs():
    """Очищает все конфиги при первом запуске"""
    configs_db.clear()
    configs_db['1_month'] = []
    configs_db['2_months'] = []
    configs_db['3_months'] = []
    save_data('configs.json', configs_db)
    print("✅ Все конфиги очищены!")

# Очищаем конфиги при первом запуске
if not configs_db:
    reset_configs()

# --- МОДЕЛИ ДАННЫХ ---
# users_db: { user_id: { 'balance': 0, 'subscription_end': None, 'referred_by': None, 'username': '...', 'first_name': '...', 'referrals_count': 0, 'used_configs': [] } }
# configs_db: { '1_month': [ { 'name': 'Germany 1', 'image': 'url_to_image', 'code': 'config_code', 'link': 'link_to_config', 'added_by': 'admin_username', 'used': False }, ... ], '2_months': [], '3_months': [] }
# payments_db: { payment_id: { 'user_id': ..., 'amount': ..., 'status': 'pending/confirmed/rejected', 'screenshot_id': ..., 'timestamp': ..., 'period': ... } }

# --- ГЕНЕРАТОР УНИКАЛЬНОГО ID ДЛЯ ПЛАТЕЖЕЙ ---
def generate_payment_id():
    return str(int(time.time() * 100000))

# --- ФУНКЦИИ ---
def get_available_config(period):
    """Находит первый неиспользованный конфиг для периода"""
    if period not in configs_db or not configs_db[period]:
        return None
    
    for config in configs_db[period]:
        if not config.get('used', False):
            return config
    return None

def mark_config_used(period, config_link):
    """Помечает конфиг как использованный"""
    if period not in configs_db:
        return False
    
    for config in configs_db[period]:
        if config['link'] == config_link:
            config['used'] = True
            save_data('configs.json', configs_db)
            return True
    return False

def get_subscription_days_left(user_id):
    """Возвращает количество дней до окончания подписки"""
    user_info = users_db.get(str(user_id), {})
    subscription_end = user_info.get('subscription_end')
    
    if not subscription_end:
        return 0
    
    end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
    now = datetime.datetime.now()
    
    if end_date <= now:
        return 0
    
    days_left = (end_date - now).days
    return max(0, days_left)

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
        types.InlineKeyboardButton("Очистить все конфиги", callback_data="admin_clear_all_configs"),
        types.InlineKeyboardButton("Назад в меню", callback_data="main_menu")
    )
    return markup

def manage_configs_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Добавить конфиг", callback_data="admin_add_config"),
        types.InlineKeyboardButton("Удалить конфиг", callback_data="admin_delete_config"),
        types.InlineKeyboardButton("Показать конфиги", callback_data="admin_show_configs"),
        types.InlineKeyboardButton("Сбросить использование конфигов", callback_data="admin_reset_configs"),
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

def payment_methods_keyboard(period_callback_data, amount, user_balance, user_id):
    # Конвертируем в Stars (1 звезда = 1.5 рубля)
    stars_amount = int(amount / STARS_TO_RUB)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Если на балансе есть деньги, показываем оплату с баланса
    if user_balance > 0:
        needed_amount = max(0, amount - user_balance)
        if needed_amount == 0:
            markup.add(types.InlineKeyboardButton(f"💳 Оплата с баланса ({amount} ₽)", callback_data=f"pay_balance_{period_callback_data}"))
        else:
            markup.add(types.InlineKeyboardButton(f"💳 Частичная оплата с баланса ({user_balance} ₽ из {amount} ₽)", callback_data=f"pay_partial_{period_callback_data}"))
    
    markup.add(
        types.InlineKeyboardButton(f"💳 Оплата картой ({amount} ₽)", callback_data=f"pay_card_{period_callback_data}"),
        types.InlineKeyboardButton(f"⭐ Оплата Telegram Stars ({stars_amount} Stars)", callback_data=f"pay_stars_{period_callback_data}"),
        types.InlineKeyboardButton("Назад", callback_data="buy_vpn")
    )
    return markup

def partial_payment_keyboard(period_data, user_balance, amount):
    """Клавиатура для частичной оплаты"""
    needed_amount = amount - user_balance
    stars_amount = int(needed_amount / STARS_TO_RUB)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"💳 Доплатить картой ({needed_amount} ₽)", callback_data=f"pay_card_partial_{period_data}"),
        types.InlineKeyboardButton(f"⭐ Доплатить Stars ({stars_amount} Stars)", callback_data=f"pay_stars_partial_{period_data}"),
        types.InlineKeyboardButton("Назад", callback_data=f"choose_period_{period_data}")
    )
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
            # Показываем кнопки для каждого периода
            markup.add(types.InlineKeyboardButton("Конфиг на 1 месяц", callback_data="get_config_1_month"))
            markup.add(types.InlineKeyboardButton("Конфиг на 2 месяца", callback_data="get_config_2_months"))
            markup.add(types.InlineKeyboardButton("Конфиг на 3 месяца", callback_data="get_config_3_months"))
    
    markup.add(types.InlineKeyboardButton("Назад", callback_data="my_account"))
    return markup

# --- ФУНКЦИЯ ВЫДАЧИ КОНФИГА ---
def send_config_to_user(user_id, period, username, first_name):
    """Выдает конфиг пользователю и сохраняет информацию о выдаче"""
    config = get_available_config(period)
    if not config:
        return False, "Нет доступных конфигов для этого периода"
    
    # Помечаем конфиг как использованный
    mark_config_used(period, config['link'])
    
    # Генерируем уникальное имя для конфига
    config_name = f"{first_name} ({username}) - {period.replace('_', ' ')}"
    
    # Сохраняем информацию о выданном конфиге
    if 'used_configs' not in users_db[str(user_id)]:
        users_db[str(user_id)]['used_configs'] = []
    
    used_config = {
        'config_name': config['name'],
        'config_link': config['link'],
        'config_code': config['code'],
        'period': period,
        'issue_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user_name': f"{first_name} (@{username})"
    }
    
    users_db[str(user_id)]['used_configs'].append(used_config)
    save_data('users.json', users_db)
    
    # Отправляем конфиг пользователю
    try:
        bot.send_message(user_id, f"🔐 **Ваш VPN конфиг**\n\n"
                                 f"👤 **Имя:** {config_name}\n"
                                 f"📅 **Период:** {period.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}\n"
                                 f"🔗 **Ссылка на конфиг:** {config['link']}\n\n"
                                 f"💾 _Сохраните этот конфиг для использования_",
                         parse_mode='Markdown')
        return True, config
    except Exception as e:
        return False, f"Ошибка отправки: {e}"

# --- ОБРАБОТЧИК КОМАНДЫ /start ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username if message.from_user.username else 'N/A'
    first_name = message.from_user.first_name if message.from_user.first_name else 'N/A'

    if user_id not in users_db:
        referred_by_id = None
        if len(message.text.split()) > 1:
            try:
                potential_referrer_id = message.text.split()[1]
                if potential_referrer_id in users_db and potential_referrer_id != user_id:
                    referred_by_id = potential_referrer_id
                    
                    # Начисляем бонусы за реферала
                    users_db[potential_referrer_id]['referrals_count'] = users_db[potential_referrer_id].get('referrals_count', 0) + 1
                    users_db[potential_referrer_id]['balance'] = users_db[potential_referrer_id].get('balance', 0) + REFERRAL_BONUS_REFERRER
                    
                    # Добавляем дни подписки рефереру, если у него есть активная подписка
                    if users_db[potential_referrer_id].get('subscription_end'):
                        current_end = datetime.datetime.strptime(users_db[potential_referrer_id]['subscription_end'], '%Y-%m-%d %H:%M:%S')
                        new_end = current_end + datetime.timedelta(days=REFERRAL_BONUS_DAYS)
                        users_db[potential_referrer_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
                        bot.send_message(potential_referrer_id, 
                                         f"🎉 Ваш реферал @{username} зарегистрировался по вашей ссылке! "
                                         f"Вам начислено {REFERRAL_BONUS_REFERRER} ₽ на баланс и {REFERRAL_BONUS_DAYS} дней к подписке!")
                    else:
                        bot.send_message(potential_referrer_id, 
                                         f"🎉 Ваш реферал @{username} зарегистрировался по вашей ссылке! "
                                         f"Вам начислено {REFERRAL_BONUS_REFERRER} ₽ на баланс.")

                    save_data('users.json', users_db)
            except ValueError:
                pass # Если реферальный ID некорректен

        users_db[user_id] = {
            'balance': REFERRAL_BONUS_NEW_USER,  # Новый пользователь получает 50 руб
            'subscription_end': None,
            'referred_by': referred_by_id,
            'username': username,
            'first_name': first_name,
            'referrals_count': 0,
            'used_configs': []
        }
        save_data('users.json', users_db)
        
        # Приветственное сообщение с бонусом
        welcome_text = f"Привет! Добро пожаловать в VPN Bot!\n\n🎁 Вам начислен приветственный бонус: {REFERRAL_BONUS_NEW_USER} ₽ на баланс!"
        if referred_by_id:
            welcome_text += f"\n🤝 Вы зарегистрировались по реферальной ссылке!"
        
        bot.send_message(message.chat.id, welcome_text,
                         reply_markup=main_menu_keyboard(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "Привет! С возвращением в VPN Bot!",
                         reply_markup=main_menu_keyboard(message.from_user.id))

# --- ОБРАБОТЧИК CALLBACK-КНОПОК ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    if call.data == "main_menu":
        bot.edit_message_text("Главное меню:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=main_menu_keyboard(user_id))
    
    # --- ПОКУПКА VPN ---
    elif call.data == "buy_vpn":
        bot.edit_message_text("Выберите срок подписки:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=buy_vpn_keyboard())
    
    elif call.data.startswith("choose_period_"):
        period_data = call.data.replace("choose_period_", "") # 1_month, 2_months, 3_months
        amount = 0
        if period_data == "1_month":
            amount = PRICE_MONTH
        elif period_data == "2_months":
            amount = PRICE_2_MONTHS
        elif period_data == "3_months":
            amount = PRICE_3_MONTHS
        
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        days_left = get_subscription_days_left(user_id)
        
        message_text = f"Вы выбрали подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}.\n"
        message_text += f"💳 К оплате: {amount} ₽\n"
        message_text += f"💰 Ваш баланс: {user_balance} ₽\n"
        
        if user_balance > 0:
            needed = amount - user_balance
            if needed > 0:
                message_text += f"💸 Можно оплатить частично: {user_balance} ₽ с баланса + {needed} ₽ доплата\n"
            else:
                message_text += f"✅ Хватает для полной оплаты с баланса!\n"
        
        if days_left > 0:
            message_text += f"📅 Текущая подписка активна еще: {days_left} дней\n"
        
        message_text += f"\nВыберите способ оплаты:"
        
        bot.edit_message_text(message_text, 
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id,
                              reply_markup=payment_methods_keyboard(period_data, amount, user_balance, user_id))

    elif call.data.startswith("pay_balance_"):
        period_data = call.data.replace("pay_balance_", "")
        amount = 0
        if period_data == "1_month":
            amount = PRICE_MONTH
        elif period_data == "2_months":
            amount = PRICE_2_MONTHS
        elif period_data == "3_months":
            amount = PRICE_3_MONTHS
        
        user_info = users_db.get(user_id, {})
        user_balance = user_info.get('balance', 0)
        
        if user_balance >= amount:
            # Списание с баланса
            users_db[user_id]['balance'] = user_balance - amount
            
            # Обновляем подписку
            current_end = user_info.get('subscription_end')
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
            save_data('users.json', users_db)

            # Выдаем конфиг
            success, result = send_config_to_user(user_id, period_data, 
                                                user_info.get('username', 'user'), 
                                                user_info.get('first_name', 'User'))
            
            if success:
                bot.edit_message_text(f"✅ Оплата прошла успешно!\n"
                                      f"💳 Списано с баланса: {amount} ₽\n"
                                      f"💰 Остаток на балансе: {user_balance - amount} ₽\n"
                                      f"📅 Подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                      f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                      chat_id=call.message.chat.id, 
                                      message_id=call.message.message_id,
                                      reply_markup=main_menu_keyboard(user_id))
            else:
                bot.edit_message_text(f"✅ Оплата прошла успешно, но возникла ошибка при выдаче конфига: {result}\n"
                                      f"Обратитесь в поддержку: @Gl1ch555",
                                      chat_id=call.message.chat.id, 
                                      message_id=call.message.message_id,
                                      reply_markup=main_menu_keyboard(user_id))
        else:
            bot.edit_message_text(f"❌ Недостаточно средств на балансе!\n"
                                  f"💰 Ваш баланс: {user_balance} ₽\n"
                                  f"💳 Требуется: {amount} ₽\n"
                                  f"💸 Не хватает: {amount - user_balance} ₽",
                                  chat_id=call.message.chat.id, 
                                  message_id=call.message.message_id)

    elif call.data.startswith("pay_partial_"):
        period_data = call.data.replace("pay_partial_", "")
        amount = 0
        if period_data == "1_month":
            amount = PRICE_MONTH
        elif period_data == "2_months":
            amount = PRICE_2_MONTHS
        elif period_data == "3_months":
            amount = PRICE_3_MONTHS
        
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        needed_amount = amount - user_balance
        
        message_text = f"💳 **Частичная оплата подписки**\n\n"
        message_text += f"📅 Период: {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}\n"
        message_text += f"💰 Общая стоимость: {amount} ₽\n"
        message_text += f"💸 Ваш баланс: {user_balance} ₽\n"
        message_text += f"🔶 Необходимо доплатить: {needed_amount} ₽\n\n"
        message_text += f"Выберите способ доплаты:"
        
        bot.edit_message_text(message_text,
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=partial_payment_keyboard(period_data, user_balance, amount))

    elif call.data.startswith("pay_card_partial_"):
        period_data = call.data.replace("pay_card_partial_", "")
        amount = 0
        if period_data == "1_month":
            amount = PRICE_MONTH
        elif period_data == "2_months":
            amount = PRICE_2_MONTHS
        elif period_data == "3_months":
            amount = PRICE_3_MONTHS
        
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        needed_amount = amount - user_balance
        
        payment_id = generate_payment_id()
        payments_db[payment_id] = {
            'user_id': user_id,
            'amount': needed_amount,
            'status': 'pending',
            'screenshot_id': None,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'period': period_data,
            'method': 'card_partial',
            'user_balance_used': user_balance
        }
        save_data('payments.json', payments_db)

        bot.edit_message_text(f"💳 **Частичная оплата картой**\n\n"
                              f"Для доплаты {needed_amount} ₽ за подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}:\n\n"
                              f"1. Переведите {needed_amount} ₽ на карту: `{CARD_NUMBER}`\n"
                              f"Держатель: `{CARD_HOLDER}`\n\n"
                              f"2. **ОБЯЗАТЕЛЬНО** отправьте скриншот перевода в этот чат.\n\n"
                              f"После подтверждения платежа:\n"
                              f"• С вашего баланса спишется {user_balance} ₽\n"
                              f"• Будет активирована подписка\n"
                              f"• Вы получите конфиг\n\n"
                              f"**Ваш платеж может быть подтвержден с задержкой, ожидайте, пожалуйста.**",
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id,
                              parse_mode='Markdown')
        
        # Уведомляем админа о частичном платеже
        bot.send_message(ADMIN_ID, 
                         f"🔔 Частичный платеж на {needed_amount} ₽ от @{call.from_user.username} (ID: {user_id})\n"
                         f"Период: {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}\n"
                         f"Баланс пользователя: {user_balance} ₽\n"
                         f"Ожидает скриншот.", 
                         reply_markup=main_menu_keyboard(ADMIN_ID))

    elif call.data.startswith("pay_stars_partial_"):
        period_data = call.data.replace("pay_stars_partial_", "")
        amount = 0
        if period_data == "1_month":
            amount = PRICE_MONTH
        elif period_data == "2_months":
            amount = PRICE_2_MONTHS
        elif period_data == "3_months":
            amount = PRICE_3_MONTHS
        
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        needed_amount = amount - user_balance
        
        # Конвертируем в Stars (1 звезда = 1.5 рубля)
        stars_amount = int(needed_amount / STARS_TO_RUB)
        
        # Создаем инвойс для оплаты Stars
        try:
            prices = [types.LabeledPrice(label=f"Доплата за VPN подписку", amount=stars_amount)]  # В звездах
            
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"Доплата за VPN подписку",
                description=f"Доплата {needed_amount} ₽ за подписку на {period_data.replace('_', ' ')}",
                provider_token='',  # Для Stars не нужен provider_token
                currency='XTR',  # Код валюты для Telegram Stars
                prices=prices,
                start_parameter=f'vpn_partial_{period_data}',
                invoice_payload=f'vpn_partial_{period_data}_{user_id}_{user_balance}'
            )
        except Exception as e:
            bot.edit_message_text(f"Ошибка при создании платежа Stars: {e}\nПожалуйста, используйте оплату картой.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id)

    elif call.data.startswith("pay_card_"):
        period_data = call.data.replace("pay_card_", "")
        amount = 0
        if period_data == "1_month":
            amount = PRICE_MONTH
        elif period_data == "2_months":
            amount = PRICE_2_MONTHS
        elif period_data == "3_months":
            amount = PRICE_3_MONTHS
        
        payment_id = generate_payment_id()
        payments_db[payment_id] = {
            'user_id': user_id,
            'amount': amount,
            'status': 'pending',
            'screenshot_id': None,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'period': period_data,
            'method': 'card'
        }
        save_data('payments.json', payments_db)

        bot.edit_message_text(f"Для оплаты {amount} ₽ за подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}:"
                              f"\n\n1. Переведите {amount} ₽ на карту: `{CARD_NUMBER}`"
                              f"\nДержатель: `{CARD_HOLDER}`"
                              f"\n\n2. **ОБЯЗАТЕЛЬНО** отправьте скриншот перевода в этот чат."
                              f"\n\nПосле получения скриншота администратор проверит платеж и подтвердит вашу подписку."
                              f"\n**Ваш платеж может быть подтвержден с задержкой, ожидайте, пожалуйста.**",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown')
        
        # Уведомляем админа о новом платеже
        bot.send_message(ADMIN_ID, 
                         f"🔔 Новый платеж на {amount} ₽ от @{call.from_user.username} (ID: {user_id}) за {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}. "
                         f"Ожидает скриншот.", 
                         reply_markup=main_menu_keyboard(ADMIN_ID))

    elif call.data.startswith("pay_stars_"):
        period_data = call.data.replace("pay_stars_", "")
        amount = 0
        if period_data == "1_month":
            amount = PRICE_MONTH
        elif period_data == "2_months":
            amount = PRICE_2_MONTHS
        elif period_data == "3_months":
            amount = PRICE_3_MONTHS
        
        # Конвертируем в Stars (1 звезда = 1.5 рубля)
        stars_amount = int(amount / STARS_TO_RUB)
        
        # Создаем инвойс для оплаты Stars
        try:
            prices = [types.LabeledPrice(label=f"VPN подписку на {period_data.replace('_', ' ')}", amount=stars_amount)]  # В звездах
            
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"VPN подписка на {period_data.replace('_', ' ')}",
                description=f"VPN подписка на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}",
                provider_token='',  # Для Stars не нужен provider_token
                currency='XTR',  # Код валюты для Telegram Stars
                prices=prices,
                start_parameter=f'vpn_subscription_{period_data}',
                invoice_payload=f'vpn_subscription_{period_data}_{user_id}'
            )
        except Exception as e:
            bot.edit_message_text(f"Ошибка при создании платежа Stars: {e}\nПожалуйста, используйте оплату картой.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id)

    # --- ЛИЧНЫЙ КАБИНЕТ ---
    elif call.data == "my_account":
        user_info = users_db.get(user_id, {})
        subscription_end = user_info.get('subscription_end')
        balance = user_info.get('balance', 0)
        days_left = get_subscription_days_left(user_id)

        status_text = "❌ Нет активной подписки"
        if days_left > 0:
            end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
            status_text = f"✅ Активна еще {days_left} дней (до {end_date.strftime('%d.%m.%Y')})"

        bot.edit_message_text(f"👤 **Ваш личный кабинет**\n\n"
                              f"📊 **Статус подписки:** {status_text}\n"
                              f"💰 **Баланс:** {balance} ₽\n"
                              f"👨 **Ваше имя:** {user_info.get('first_name', 'N/A')}\n"
                              f"📱 **Username:** @{user_info.get('username', 'N/A')}\n"
                              f"🤝 **Рефералов приглашено:** {user_info.get('referrals_count', 0)}\n\n",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown',
                              reply_markup=my_account_keyboard())

    elif call.data == "my_configs":
        bot.edit_message_text("Выберите конфиг для получения:",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=my_configs_keyboard(user_id))

    elif call.data.startswith("get_config_"):
        period_data = call.data.replace("get_config_", "")
        user_info = users_db.get(user_id, {})
        
        # Проверяем активную подписку
        days_left = get_subscription_days_left(user_id)
        if days_left <= 0:
            bot.send_message(call.message.chat.id, "❌ У вас нет активной подписки или подписка истекла.")
            return
        
        # Выдаем конфиг
        success, result = send_config_to_user(user_id, period_data, 
                                            user_info.get('username', 'user'), 
                                            user_info.get('first_name', 'User'))
        
        if success:
            bot.send_message(call.message.chat.id, "✅ Конфиг успешно выдан! Проверьте сообщения выше.")
        else:
            bot.send_message(call.message.chat.id, f"❌ {result}")

    # --- ПОДДЕРЖКА ---
    elif call.data == "support":
        bot.edit_message_text(f"Для связи с поддержкой напишите @Gl1ch555.\n"
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
                              f"  🎁 **Новому пользователю** начисляется {REFERRAL_BONUS_NEW_USER} ₽ на баланс\n"
                              f"  💰 **Вам** начисляется {REFERRAL_BONUS_REFERRER} ₽ на баланс\n"
                              f"  📅 **Вам** добавляется {REFERRAL_BONUS_DAYS} дней к активной подписке\n\n"
                              f"💰 **Ваши бонусы:**\n"
                              f"• Рефералов приглашено: {referrals_count}\n"
                              f"• Заработано: {referrals_count * REFERRAL_BONUS_REFERRER} ₽\n"
                              f"• Текущий баланс: {balance} ₽\n\n"
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

    elif call.data == "admin_clear_all_configs":
        if str(user_id) == str(ADMIN_ID):
            reset_configs()
            bot.send_message(call.message.chat.id, "✅ Все конфиги очищены! Теперь можно добавить новые.",
                           reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

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
                    available_count = sum(1 for config in configs_list if not config.get('used', False))
                    message_text += f"  Всего: {len(configs_list)}, Доступно: {available_count}\n"
                    for i, config in enumerate(configs_list):
                        status = "✅" if not config.get('used', False) else "❌"
                        message_text += f"  {i+1}. {status} {config['name']} - `{config['link']}`\n"
                else:
                    message_text += "  (Нет конфигов)\n"
            
            bot.edit_message_text(message_text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown', reply_markup=manage_configs_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_reset_configs":
        if str(user_id) == str(ADMIN_ID):
            reset_count = 0
            for period in configs_db:
                for config in configs_db[period]:
                    if config.get('used', False):
                        config['used'] = False
                        reset_count += 1
            save_data('configs.json', configs_db)
            bot.send_message(call.message.chat.id, f"✅ Сброшено использование {reset_count} конфигов.",
                           reply_markup=manage_configs_keyboard())
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
                                 f"Отправьте ссылки на конфиги, каждую с новой строки.\n"
                                 f"Имена будут сгенерированы автоматически на основе username пользователей.",
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

    elif call.data == "admin_confirm_payments":
        if str(user_id) == str(ADMIN_ID):
            pending_payments = {pid: p_data for pid, p_data in payments_db.items() if p_data['status'] == 'pending' and p_data['screenshot_id']}
            if not pending_payments:
                bot.edit_message_text("Нет платежей, ожидающих подтверждения со скриншотами.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_keyboard())
                return
            
            for payment_id, p_data in pending_payments.items():
                user_payment = users_db.get(p_data['user_id'])
                if user_payment:
                    payment_type = "💳 Обычный платеж"
                    if p_data['method'] == 'card_partial':
                        payment_type = "🔶 Частичный платеж"
                        payment_type += f" (баланс: {p_data.get('user_balance_used', 0)} ₽)"
                    
                    bot.send_photo(ADMIN_ID, p_data['screenshot_id'], 
                                   caption=f"{payment_type}\n"
                                           f"ID: {payment_id}\n"
                                           f"От: @{user_payment.get('username', 'N/A')} (ID: {p_data['user_id']})\n"
                                           f"Сумма: {p_data['amount']} ₽\n"
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
                payment_method = payments_db[payment_id]['method']
                
                # Для частичных платежей списываем баланс
                if payment_method == 'card_partial':
                    user_balance_used = payments_db[payment_id].get('user_balance_used', 0)
                    if target_user_id in users_db and user_balance_used > 0:
                        users_db[target_user_id]['balance'] = max(0, users_db[target_user_id].get('balance', 0) - user_balance_used)
                
                # Обновляем подписку пользователя
                if target_user_id in users_db:
                    current_end = users_db[target_user_id].get('subscription_end')
                    if current_end:
                        current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
                    else:
                        current_end = datetime.datetime.now()

                    add_days = 0
                    if period_data == '1_month': add_days = 30
                    elif period_data == '2_months': add_days = 60
                    elif period_data == '3_months': add_days = 90
                    
                    new_end = current_end + datetime.timedelta(days=add_days)
                    users_db[target_user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
                    save_data('users.json', users_db)

                    # Выдаем конфиг после подтверждения платежа
                    user_info = users_db[target_user_id]
                    success, result = send_config_to_user(target_user_id, period_data, 
                                                        user_info.get('username', 'user'), 
                                                        user_info.get('first_name', 'User'))
                    
                    if success:
                        if payment_method == 'card_partial':
                            user_balance_used = payments_db[payment_id].get('user_balance_used', 0)
                            bot.send_message(target_user_id, 
                                             f"✅ Ваш частичный платеж подтвержден!\n"
                                             f"💳 Доплачено картой: {payments_db[payment_id]['amount']} ₽\n"
                                             f"💰 Списано с баланса: {user_balance_used} ₽\n"
                                             f"📅 Подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                             f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                             reply_markup=main_menu_keyboard(target_user_id))
                        else:
                            bot.send_message(target_user_id, 
                                             f"✅ Ваш платеж за подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')} подтвержден!\n"
                                             f"Ваша подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                             f"Конфиг уже выдан! Проверьте сообщения выше.",
                                             reply_markup=main_menu_keyboard(target_user_id))
                    else:
                        bot.send_message(target_user_id, 
                                         f"✅ Платеж подтвержден, но возникла ошибка при выдаче конфига: {result}\n"
                                         f"Обратитесь в поддержку: @Gl1ch555")
                
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
                payments_db[payment_id]['status'] = 'rejected'
                save_data('payments.json', payments_db)
                
                target_user_id = payments_db[payment_id]['user_id']
                bot.send_message(target_user_id, 
                                 f"❌ Ваш платеж (ID: {payment_id}) был отклонен администратором. "
                                 f"Пожалуйста, свяжитесь с поддержкой (@Gl1ch555) для уточнения.",
                                 reply_markup=main_menu_keyboard(target_user_id))
                
                bot.edit_message_text(f"Платеж {payment_id} отклонен.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            else:
                bot.edit_message_text("Платеж уже обработан или не найден.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    # ... остальные обработчики админки ...

# --- ОБРАБОТЧИК ПРЕДОПЛАТЫ (Telegram Stars) ---
@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    user_id = str(message.from_user.id)
    payment_info = message.successful_payment
    
    # Обработка частичных платежей Stars
    if 'partial' in payment_info.invoice_payload:
        payload_parts = payment_info.invoice_payload.split('_')
        if len(payload_parts) >= 5:
            period_data = payload_parts[2] + '_' + payload_parts[3]
            user_balance_used = int(payload_parts[4])
            
            # Создаем запись о платеже
            payment_id = generate_payment_id()
            payments_db[payment_id] = {
                'user_id': user_id,
                'amount': payment_info.total_amount * STARS_TO_RUB,  # Конвертируем обратно в рубли
                'status': 'confirmed',
                'screenshot_id': None,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period': period_data,
                'method': 'stars_partial',
                'user_balance_used': user_balance_used
            }
            save_data('payments.json', payments_db)
            
            # Списание баланса
            if user_id in users_db:
                users_db[user_id]['balance'] = max(0, users_db[user_id].get('balance', 0) - user_balance_used)
            
            # Обновляем подписку пользователя
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
                save_data('users.json', users_db)

                # Выдаем конфиг
                user_info = users_db[user_id]
                success, result = send_config_to_user(user_id, period_data, 
                                                    user_info.get('username', 'user'), 
                                                    user_info.get('first_name', 'User'))
                
                if success:
                    bot.send_message(user_id, 
                                     f"✅ Частичная оплата Stars прошла успешно!\n"
                                     f"⭐ Доплачено Stars: {payment_info.total_amount}\n"
                                     f"💰 Списано с баланса: {user_balance_used} ₽\n"
                                     f"📅 Подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                     f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                     reply_markup=main_menu_keyboard(user_id))
                else:
                    bot.send_message(user_id, 
                                     f"✅ Оплата прошла успешно, но возникла ошибка при выдаче конфига: {result}\n"
                                     f"Обратитесь в поддержку: @Gl1ch555")
    else:
        # Обычные платежи Stars
        payload_parts = payment_info.invoice_payload.split('_')
        if len(payload_parts) >= 4:
            period_data = payload_parts[2] + '_' + payload_parts[3]
            
            # Создаем запись о платеже
            payment_id = generate_payment_id()
            payments_db[payment_id] = {
                'user_id': user_id,
                'amount': payment_info.total_amount * STARS_TO_RUB,  # Конвертируем обратно в рубли
                'status': 'confirmed',
                'screenshot_id': None,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period': period_data,
                'method': 'stars'
            }
            save_data('payments.json', payments_db)
            
            # Обновляем подписку пользователя
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
                save_data('users.json', users_db)

                # Выдаем конфиг
                user_info = users_db[user_id]
                success, result = send_config_to_user(user_id, period_data, 
                                                    user_info.get('username', 'user'), 
                                                    user_info.get('first_name', 'User'))
                
                if success:
                    bot.send_message(user_id, 
                                     f"✅ Ваш платеж за подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')} подтвержден!\n"
                                     f"⭐ Оплачено: {payment_info.total_amount} Stars\n"
                                     f"📅 Ваша подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                     f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                     reply_markup=main_menu_keyboard(user_id))
                else:
                    bot.send_message(user_id, 
                                     f"✅ Платеж подтвержден, но возникла ошибка при выдаче конфига: {result}\n"
                                     f"Обратитесь в поддержку: @Gl1ch555")

# --- ОБРАБОТКА КОРРЕКТНОЙ ОСТАНОВКИ ---
def signal_handler(signum, frame):
    print(f"Получен сигнал {signum}. Корректно останавливаю бота...")
    bot.stop_polling()
    print("Бот остановлен.")
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler) # systemctl stop

# --- ЗАПУСК БОТА ---
if __name__ == "__main__":
    print("Бот запускается...")
    print("✅ Все конфиги очищены! Добавьте новые через админ-панель.")
    try:
        bot.polling(none_stop=True, interval=0, timeout=60)
    except KeyboardInterrupt:
        print("Бот остановлен пользователем (Ctrl+C).")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        print("Бот будет перезапущен через systemd.")
