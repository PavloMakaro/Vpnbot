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
import uuid # Для уникальных ID

# --- CONFIGURATION (from environment variables for security) ---
TOKEN = os.getenv('BOT_TOKEN', 'YOUR_DEFAULT_TOKEN_HERE') # Замените на реальный токен в переменной окружения
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', '@Gl1ch555')
ADMIN_ID = int(os.getenv('ADMIN_ID', '8320218178')) # Замените на ваш фактический ID администратора
CARD_NUMBER = os.getenv('CARD_NUMBER', '2204320690808227')
CARD_HOLDER = os.getenv('CARD_HOLDER', 'Makarov Pavel Alexandrovich (Ozon Bank)')

# Prices
PRICE_MONTH = 50
PRICE_2_MONTHS = 90
PRICE_3_MONTHS = 120

# Referral bonuses
REFERRAL_BONUS_NEW_USER = 50 # Если для всех, кто зарегистрировался
REFERRAL_BONUS_REFERRER = 25
REFERRAL_BONUS_DAYS = 7

STARS_TO_RUB = 1.5

# Centralized period info
PERIOD_INFO = {
    "1_month": {"price": PRICE_MONTH, "days": 30, "name_ru": "1 месяц"},
    "2_months": {"price": PRICE_2_MONTHS, "days": 60, "name_ru": "2 месяца"},
    "3_months": {"price": PRICE_3_MONTHS, "days": 90, "name_ru": "3 месяца"},
}

# --- Bot Initialization ---
bot = telebot.TeleBot(TOKEN)

# --- Data Management ---
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True) # Ensure data directory exists

def load_data(filename):
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(filename, data):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

users_db = load_data('users.json')
configs_db = load_data('configs.json')
payments_db = load_data('payments.json')

# --- CONFIGS RESET LOGIC IMPROVEMENT ---
# This block is now handled more carefully.
# If you want to reset 'used' status for ALL configs:
# for period_key in configs_db:
#     for config_item in configs_db[period_key]:
#         config_item['used'] = False
# save_data('configs.json', configs_db)
# print("All configs 'used' status reset on startup.")

# If you want to purge configs, it should be a manual admin action, not on every startup.
# For now, commenting out the full reset you had:
# configs_db = {
#     '1_month': [],
#     '2_months': [],
#     '3_months': []
# }
# save_data('configs.json', configs_db)


# --- Helper Functions ---
def get_payment_id():
    return str(uuid.uuid4()) # More robust unique ID

def get_period_price(period):
    return PERIOD_INFO.get(period, {}).get("price", 0)

def get_period_days(period):
    return PERIOD_INFO.get(period, {}).get("days", 0)

def get_period_name_ru(period):
    return PERIOD_INFO.get(period, {}).get("name_ru", period.replace('_', ' '))

def get_available_config(period):
    if period not in configs_db:
        return None
    
    for config in configs_db[period]:
        if not config.get('used', False):
            return config
    return None

def mark_config_used(period, config_link):
    if period not in configs_db:
        return False
    
    for config in configs_db[period]:
        if config['link'] == config_link:
            config['used'] = True
            save_data('configs.json', configs_db)
            return True
    return False

def get_subscription_days_left(user_id):
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

# --- Decorators ---
def admin_only(func):
    def wrapper(call_or_message, *args, **kwargs):
        user_id = str(call_or_message.from_user.id)
        if user_id == str(ADMIN_ID):
            return func(call_or_message, *args, **kwargs)
        else:
            chat_id = call_or_message.chat.id if isinstance(call_or_message, types.Message) else call_or_message.message.chat.id
            bot.answer_callback_query(call_or_message.id, "У вас нет прав администратора.") # For callback queries
            bot.send_message(chat_id, "У вас нет прав администратора.") # For messages
    return wrapper

# --- Keyboards ---
# (Сохранил ваши клавиатуры, но они могут быть пересмотрены для лучшего UX)

def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Управление конфигами", callback_data="admin_manage_configs"),
        types.InlineKeyboardButton("Подтвердить платежи", callback_data="admin_confirm_payments"),
        types.InlineKeyboardButton("Управление пользователями", callback_data="admin_manage_users"),
        types.InlineKeyboardButton("Управление конфигами пользователей", callback_data="admin_manage_user_configs"),
        types.InlineKeyboardButton("Рассылка", callback_data="admin_broadcast"),
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

def payment_methods_keyboard(period_callback_data, amount, user_balance):
    stars_amount = int(amount / STARS_TO_RUB)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    needed_amount = max(0, amount - user_balance)
    if needed_amount == 0:
        markup.add(types.InlineKeyboardButton(f"💳 Оплата с баланса ({amount} ₽)", callback_data=f"pay_balance_{period_callback_data}"))
    else:
        markup.add(types.InlineKeyboardButton(f"💳 Оплата с баланса ({user_balance} ₽ + доплатить {needed_amount} ₽)", callback_data=f"pay_balance_{period_callback_data}"))
    
    markup.add(
        types.InlineKeyboardButton(f"💳 Оплата картой ({amount} ₽)", callback_data=f"pay_card_{period_callback_data}"),
        types.InlineKeyboardButton(f"⭐ Оплата Telegram Stars ({stars_amount} Stars)", callback_data=f"pay_stars_{period_callback_data}"),
        types.InlineKeyboardButton("Назад", callback_data="buy_vpn")
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
    
    user_info = users_db.get(str(user_id), {})
    subscription_end = user_info.get('subscription_end')
    
    if subscription_end:
        end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
        if end_date > datetime.datetime.now():
            markup.add(types.InlineKeyboardButton("Получить конфиг на 1 месяц", callback_data="get_config_1_month"))
            markup.add(types.InlineKeyboardButton("Получить конфиг на 2 месяца", callback_data="get_config_2_months"))
            markup.add(types.InlineKeyboardButton("Получить конфиг на 3 месяца", callback_data="get_config_3_months"))
        else:
            markup.add(types.InlineKeyboardButton("Продлить подписку для получения конфига", callback_data="buy_vpn"))
    else:
        markup.add(types.InlineKeyboardButton("Купить подписку для получения конфига", callback_data="buy_vpn"))
    
    markup.add(types.InlineKeyboardButton("Назад", callback_data="my_account"))
    return markup

# --- Core Logic ---
def send_config_to_user(user_id, period, username, first_name):
    config = get_available_config(period)
    if not config:
        return False, "Нет доступных конфигов для этого периода"
    
    mark_config_used(period, config['link'])
    
    display_username = f"@{username}" if username and username != 'N/A' else ""
    config_name_for_user = f"{first_name} {display_username} - {get_period_name_ru(period)}"
    
    if 'used_configs' not in users_db[str(user_id)]:
        users_db[str(user_id)]['used_configs'] = []
    
    used_config = {
        'id': get_payment_id(), # Add a unique ID for the issued config
        'config_name': config['name'], # This is the admin-generated name
        'config_link': config['link'],
        'config_code': config['code'],
        'period': period,
        'issue_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user_name': f"{first_name} {display_username}"
    }
    
    users_db[str(user_id)]['used_configs'].append(used_config)
    save_data('users.json', users_db)
    
    try:
        bot.send_message(user_id, f"🔐 **Ваш VPN конфиг**\n\n"
                                 f"👤 **Имя:** {config_name_for_user}\n"
                                 f"📅 **Период:** {get_period_name_ru(period)}\n"
                                 f"🔗 **Ссылка на конфиг:** {config['link']}\n\n"
                                 f"💾 _Сохраните этот конфиг для использования_",
                         parse_mode='Markdown')
        return True, config
    except Exception as e:
        return False, f"Ошибка отправки: {e}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username if message.from_user.username else 'N/A'
    first_name = message.from_user.first_name if message.from_user.first_name else 'N/A'

    if user_id not in users_db:
        referred_by_id = None
        welcome_text_bonus = ""

        # Everyone gets initial bonus
        initial_balance = REFERRAL_BONUS_NEW_USER 
        welcome_text_bonus = f"\n\n🎁 Вам начислен приветственный бонус: {REFERRAL_BONUS_NEW_USER} ₽ на баланс!"

        if len(message.text.split()) > 1:
            try:
                potential_referrer_id = message.text.split()[1]
                if potential_referrer_id in users_db and potential_referrer_id != user_id:
                    referred_by_id = potential_referrer_id
                    
                    users_db[potential_referrer_id]['referrals_count'] = users_db[potential_referrer_id].get('referrals_count', 0) + 1
                    users_db[potential_referrer_id]['balance'] = users_db[potential_referrer_id].get('balance', 0) + REFERRAL_BONUS_REFERRER
                    
                    referrer_sub_end = users_db[potential_referrer_id].get('subscription_end')
                    if referrer_sub_end:
                        current_end = datetime.datetime.strptime(referrer_sub_end, '%Y-%m-%d %H:%M:%S')
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
                    welcome_text_bonus += f"\n🤝 Вы зарегистрировались по реферальной ссылке!"
            except ValueError:
                pass

        users_db[user_id] = {
            'balance': initial_balance, # Initial bonus is here
            'subscription_end': None,
            'referred_by': referred_by_id,
            'username': username,
            'first_name': first_name,
            'referrals_count': 0,
            'used_configs': []
        }
        save_data('users.json', users_db)
        
        bot.send_message(message.chat.id, f"Привет! Добро пожаловать в VPN Bot!{welcome_text_bonus}",
                         reply_markup=main_menu_keyboard(message.from_user.id),
                         parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "Привет! С возвращением в VPN Bot!",
                         reply_markup=main_menu_keyboard(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data == "main_menu":
        bot.edit_message_text("Главное меню:", chat_id=chat_id, message_id=message_id,
                              reply_markup=main_menu_keyboard(user_id))
    
    elif call.data == "buy_vpn":
        bot.edit_message_text("Выберите срок подписки:", chat_id=chat_id, message_id=message_id,
                              reply_markup=buy_vpn_keyboard())
    
    elif call.data.startswith("choose_period_"):
        period_data = call.data.replace("choose_period_", "")
        amount = get_period_price(period_data)
        
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        days_left = get_subscription_days_left(user_id)
        
        message_text = f"Вы выбрали подписку на {get_period_name_ru(period_data)}.\n"
        message_text += f"💳 К оплате: {amount} ₽\n"
        message_text += f"💰 Ваш баланс: {user_balance} ₽\n"
        
        if days_left > 0:
            message_text += f"📅 Текущая подписка активна еще: {days_left} дней\n"
        
        message_text += f"\nВыберите способ оплаты:"
        
        bot.edit_message_text(message_text, 
                              chat_id=chat_id, 
                              message_id=message_id,
                              reply_markup=payment_methods_keyboard(period_data, amount, user_balance))

    elif call.data.startswith("pay_balance_"):
        period_data = call.data.replace("pay_balance_", "")
        amount = get_period_price(period_data)
        
        user_info = users_db.get(user_id, {})
        user_balance = user_info.get('balance', 0)
        
        if user_balance >= amount:
            # First, check config availability BEFORE deducting money
            temp_config_check = get_available_config(period_data)
            if not temp_config_check:
                bot.edit_message_text(f"❌ Извините, нет доступных конфигов на {get_period_name_ru(period_data)}.\n"
                                      f"Попробуйте позже или обратитесь в поддержку.",
                                      chat_id=chat_id, message_id=message_id,
                                      reply_markup=payment_methods_keyboard(period_data, amount, user_balance))
                return

            users_db[user_id]['balance'] = user_balance - amount
            
            current_end = user_info.get('subscription_end')
            if current_end:
                current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
            else:
                current_end = datetime.datetime.now()

            add_days = get_period_days(period_data)
            
            new_end = current_end + datetime.timedelta(days=add_days)
            users_db[user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            save_data('users.json', users_db)

            # Now, issue config
            success, result = send_config_to_user(user_id, period_data, 
                                                user_info.get('username', 'user'), 
                                                user_info.get('first_name', 'User'))
            
            if success:
                bot.edit_message_text(f"✅ Оплата прошла успешно!\n"
                                      f"💳 Списано с баланса: {amount} ₽\n"
                                      f"💰 Остаток на балансе: {user_balance - amount} ₽\n"
                                      f"📅 Подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                      f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                      chat_id=chat_id, 
                                      message_id=message_id)
            else:
                # This should ideally not happen if temp_config_check was successful,
                # but good to have a fallback.
                bot.edit_message_text(f"✅ Оплата прошла успешно, но возникла ошибка при выдаче конфига: {result}\n"
                                      f"Обратитесь в поддержку: @Gl1ch555",
                                      chat_id=chat_id, 
                                      message_id=message_id)
        else:
            needed_amount = amount - user_balance
            bot.edit_message_text(f"❌ Недостаточно средств на балансе!\n"
                                  f"💰 Ваш баланс: {user_balance} ₽\n"
                                  f"💳 Требуется: {amount} ₽\n"
                                  f"💸 Не хватает: {needed_amount} ₽\n"
                                  f"Пожалуйста, пополните баланс или выберите другой способ оплаты.",
                                  chat_id=chat_id, 
                                  message_id=message_id,
                                  reply_markup=payment_methods_keyboard(period_data, amount, user_balance))

    elif call.data.startswith("pay_card_"):
        period_data = call.data.replace("pay_card_", "")
        amount = get_period_price(period_data)
        
        payment_id = get_payment_id()
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

        bot.edit_message_text(f"Для оплаты {amount} ₽ за подписку на {get_period_name_ru(period_data)}:"
                              f"\n\n1. Переведите {amount} ₽ на карту: `{CARD_NUMBER}`"
                              f"\nДержатель: `{CARD_HOLDER}`"
                              f"\n\n2. **ОБЯЗАТЕЛЬНО** отправьте скриншот перевода в этот чат."
                              f"\n\nПосле получения скриншота администратор проверит платеж и подтвердит вашу подписку."
                              f"\n**Ваш платеж может быть подтвержден с задержкой, ожидайте, пожалуйста.**",
                              chat_id=chat_id, message_id=message_id,
                              parse_mode='Markdown')
        
        bot.send_message(ADMIN_ID, 
                         f"🔔 Новый платеж на {amount} ₽ от @{call.from_user.username or 'N/A'} (ID: {user_id}) за {get_period_name_ru(period_data)}. "
                         f"Ожидает скриншот.", 
                         reply_markup=admin_keyboard()) # Changed to admin_keyboard

    elif call.data.startswith("pay_stars_"):
        period_data = call.data.replace("pay_stars_", "")
        amount = get_period_price(period_data)
        stars_amount = int(amount / STARS_TO_RUB * 100) # Amount for Stars is in smallest units (e.g. cents)
        
        try:
            prices = [types.LabeledPrice(label=f"VPN подписка на {get_period_name_ru(period_data)}", amount=stars_amount)]
            
            # Check for config availability before offering payment
            temp_config_check = get_available_config(period_data)
            if not temp_config_check:
                bot.edit_message_text(f"❌ Извините, нет доступных конфигов на {get_period_name_ru(period_data)}.\n"
                                      f"Попробуйте позже или обратитесь в поддержку.",
                                      chat_id=chat_id, message_id=message_id,
                                      reply_markup=payment_methods_keyboard(period_data, amount, users_db.get(user_id, {}).get('balance', 0)))
                return

            bot.send_invoice(
                chat_id=chat_id,
                title=f"VPN подписка на {get_period_name_ru(period_data)}",
                description=f"VPN подписка на {get_period_name_ru(period_data)}",
                provider_token=os.getenv('STARS_PROVIDER_TOKEN', ''), # Use env variable for provider token
                currency='XTR',
                prices=prices,
                start_parameter=f'vpn_subscription_{period_data}',
                invoice_payload=f'vpn_subscription_{period_data}_{user_id}'
            )
        except Exception as e:
            bot.edit_message_text(f"Ошибка при создании платежа Stars: {e}\nПожалуйста, используйте оплату картой.",
                                  chat_id=chat_id, message_id=message_id)

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
                              chat_id=chat_id, message_id=message_id,
                              parse_mode='Markdown',
                              reply_markup=my_account_keyboard())

    elif call.data == "my_configs":
        bot.edit_message_text("Выберите конфиг для получения:",
                              chat_id=chat_id, message_id=message_id,
                              reply_markup=my_configs_keyboard(user_id))

    elif call.data.startswith("get_config_"):
        period_data = call.data.replace("get_config_", "")
        user_info = users_db.get(user_id, {})
        
        days_left = get_subscription_days_left(user_id)
        if days_left <= 0:
            bot.send_message(chat_id, "❌ У вас нет активной подписки или подписка истекла.")
            return
        
        success, result = send_config_to_user(user_id, period_data, 
                                            user_info.get('username', 'user'), 
                                            user_info.get('first_name', 'User'))
        
        if success:
            bot.send_message(chat_id, "✅ Конфиг успешно выдан! Проверьте сообщения выше.")
        else:
            bot.send_message(chat_id, f"❌ {result}")

    elif call.data == "support":
        bot.edit_message_text(f"Для связи с поддержкой напишите @Gl1ch555.\n"
                              f"Постараемся ответить как можно скорее.",
                              chat_id=chat_id, message_id=message_id,
                              reply_markup=main_menu_keyboard(user_id))

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
                              chat_id=chat_id, message_id=message_id,
                              parse_mode='Markdown', reply_markup=main_menu_keyboard(user_id))

    elif call.data == "admin_panel":
        if str(user_id) == str(ADMIN_ID): # No decorator here yet, as it's the entry point to admin_panel from main_menu
            bot.edit_message_text("🛠️ Админ-панель:", chat_id=chat_id, message_id=message_id,
                                  reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
            bot.edit_message_text("Главное меню:", chat_id=chat_id, message_id=message_id,
                                  reply_markup=main_menu_keyboard(user_id))

    elif call.data == "admin_manage_configs":
        bot.answer_callback_query(call.id) # Acknowledge callback for smooth UX
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Управление конфигами:", chat_id=chat_id, message_id=message_id,
                                  reply_markup=manage_configs_keyboard())
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.") # Fallback message

    elif call.data == "admin_show_configs":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            message_text = "**Текущие конфиги:**\n\n"
            for period, configs_list in configs_db.items():
                message_text += f"**{get_period_name_ru(period).capitalize()}:**\n"
                if configs_list:
                    available_count = sum(1 for config in configs_list if not config.get('used', False))
                    message_text += f"  Всего: {len(configs_list)}, Доступно: {available_count}\n"
                    for i, config in enumerate(configs_list):
                        status = "✅" if not config.get('used', False) else "❌"
                        message_text += f"  `{i+1}`. {status} {config['name']} - `{config['link']}`\n"
                else:
                    message_text += "  (Нет конфигов)\n"
            
            bot.edit_message_text(message_text, chat_id=chat_id, message_id=message_id,
                                  parse_mode='Markdown', reply_markup=manage_configs_keyboard())
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_reset_configs":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            reset_count = 0
            for period in configs_db:
                for config in configs_db[period]:
                    if config.get('used', False):
                        config['used'] = False
                        reset_count += 1
            save_data('configs.json', configs_db)
            bot.send_message(chat_id, f"✅ Сброшено использование {reset_count} конфигов.",
                           reply_markup=manage_configs_keyboard())
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_add_config":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Выберите период подписки для конфига:", 
                                 chat_id=chat_id, message_id=message_id,
                                 reply_markup=choose_period_keyboard("add_config"))
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data.startswith("add_config_"):
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            period = call.data.replace("add_config_", "")
            bot.edit_message_text(f"Добавление конфигов для периода: {get_period_name_ru(period)}\n\n"
                                 f"Отправьте ссылки на конфиги, каждую с новой строки.\n"
                                 f"Имена будут сгенерированы автоматически (например, admin_ID_N).",
                                 chat_id=chat_id, message_id=message_id)
            bot.register_next_step_handler(call.message, process_add_configs_bulk, period)
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_delete_config":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(chat_id, "Введите период и ID конфига для удаления (например, `1_month 1` для первого конфига на 1 месяц, ID начинаются с 1. Используйте `/admin_show_configs` чтобы увидеть ID).")
            bot.register_next_step_handler(call.message, process_delete_config)
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_confirm_payments":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            pending_payments = {pid: p_data for pid, p_data in payments_db.items() if p_data['status'] == 'pending' and p_data['screenshot_id']}
            if not pending_payments:
                bot.edit_message_text("Нет платежей, ожидающих подтверждения со скриншотами.", chat_id=chat_id, message_id=message_id, reply_markup=admin_keyboard())
                return
            
            # Send list of pending payments first for better UX
            payment_list_text = "**Платежи, ожидающие подтверждения:**\n\n"
            for payment_id, p_data in pending_payments.items():
                user_payment_info = users_db.get(p_data['user_id'])
                username_str = user_payment_info.get('username', 'N/A') if user_payment_info else 'N/A'
                payment_list_text += f"ID: `{payment_id}`\n" \
                                     f"От: @{username_str} (ID: {p_data['user_id']})\n" \
                                     f"Сумма: {p_data['amount']} ₽ за {get_period_name_ru(p_data['period'])}\n" \
                                     f"Время: {p_data['timestamp']}\n" \
                                     f"⚡ /review_payment_{payment_id}\n\n"
            
            bot.edit_message_text(payment_list_text + "\nНажмите на команду '/review_payment_ID' для просмотра скриншота и подтверждения.", 
                                  chat_id=chat_id, message_id=message_id, parse_mode='Markdown', 
                                  reply_markup=admin_keyboard()) # Return to admin menu after showing list
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_confirm_"):
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            payment_id = call.data.replace("admin_confirm_", "")
            if payment_id in payments_db and payments_db[payment_id]['status'] == 'pending':
                payments_db[payment_id]['status'] = 'confirmed'
                
                target_user_id = payments_db[payment_id]['user_id']
                period_data = payments_db[payment_id]['period']
                
                if target_user_id in users_db:
                    current_end = users_db[target_user_id].get('subscription_end')
                    if current_end:
                        current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
                    else:
                        current_end = datetime.datetime.now()

                    add_days = get_period_days(period_data)
                    
                    new_end = current_end + datetime.timedelta(days=add_days)
                    users_db[target_user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
                    save_data('users.json', users_db)

                    user_info = users_db[target_user_id]
                    success, result = send_config_to_user(target_user_id, period_data, 
                                                        user_info.get('username', 'user'), 
                                                        user_info.get('first_name', 'User'))
                    
                    if success:
                        bot.send_message(target_user_id, 
                                         f"✅ Ваш платеж за подписку на {get_period_name_ru(period_data)} подтвержден!\n"
                                         f"Ваша подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                         f"Конфиг уже выдан! Проверьте сообщения выше.",
                                         reply_markup=main_menu_keyboard(target_user_id))
                    else:
                        bot.send_message(target_user_id, 
                                         f"✅ Платеж подтвержден, но возникла ошибка при выдаче конфига: {result}\n"
                                         f"Обратитесь в поддержку: @Gl1ch555")
                
                save_data('payments.json', payments_db)
                bot.edit_message_text(f"Платеж {payment_id} подтвержден.", chat_id=chat_id, message_id=message_id, reply_markup=admin_keyboard())
            else:
                bot.edit_message_text("Платеж уже обработан или не найден.", chat_id=chat_id, message_id=message_id, reply_markup=admin_keyboard())
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_reject_"):
        bot.answer_callback_query(call.id)
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
                
                bot.edit_message_text(f"Платеж {payment_id} отклонен.", chat_id=chat_id, message_id=message_id, reply_markup=admin_keyboard())
            else:
                bot.edit_message_text("Платеж уже обработан или не найден.", chat_id=chat_id, message_id=message_id, reply_markup=admin_keyboard())
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_manage_users":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Управление пользователями:", 
                                 chat_id=chat_id, message_id=message_id,
                                 reply_markup=users_management_keyboard())
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_active_users":
        bot.answer_callback_query(call.id)
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
                        
                        message_text += f"👤 **{u_data.get('first_name', 'N/A')}** (@{u_data.get('username', 'N/A') or 'N/A'})\n"
                        message_text += f"🆔 ID: `{uid}`\n"
                        message_text += f"💰 Баланс: {u_data.get('balance', 0)} ₽\n"
                        message_text += f"📅 Подписка до: {sub_end.strftime('%d.%m.%Y %H:%M')}\n"
                        message_text += f"🤝 Рефералов: {u_data.get('referrals_count', 0)}\n"
                        message_text += f"📎 Приглашен: {referred_by}\n"
                        message_text += f"⚡ Действия: /manage_{uid}\n\n"
            
            if active_count == 0:
                message_text = "❌ Нет активных пользователей."
            
            # Use edit_message_text to replace previous admin menu
            bot.edit_message_text(message_text, chat_id=chat_id, message_id=message_id, parse_mode='Markdown', reply_markup=users_management_keyboard())
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_all_users":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            message_text = f"**Все пользователи ({len(users_db)}):**\n\n"
            
            for i, (uid, u_data) in enumerate(users_db.items(), 1):
                sub_status = "❌ Нет подписки"
                if u_data.get('subscription_end'):
                    sub_end = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                    if sub_end > datetime.datetime.now():
                        sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y')}"
                    else:
                        sub_status = "❌ Истекла"
                
                message_text += f"{i}. **{u_data.get('first_name', 'N/A')}** (@{u_data.get('username', 'N/A') or 'N/A'})\n"
                message_text += f"   🆔: `{uid}` | {sub_status}\n"
                message_text += f"   💰: {u_data.get('balance', 0)} ₽ | 🤝: {u_data.get('referrals_count', 0)}\n"
                message_text += f"   ⚡ /manage_{uid}\n\n"
            
            bot.edit_message_text(message_text, chat_id=chat_id, message_id=message_id, parse_mode='Markdown', reply_markup=users_management_keyboard())
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_search_user":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(chat_id, "Введите username или ID пользователя для поиска:")
            bot.register_next_step_handler(call.message, process_search_user)
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_edit_user":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(chat_id, "Введите ID пользователя, которого хотите изменить:")
            bot.register_next_step_handler(call.message, process_edit_user_id)
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_edit_balance_"):
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_edit_balance_", "")
            bot.send_message(chat_id, f"Введите новый баланс для пользователя {target_user_id}:")
            bot.register_next_step_handler(call.message, process_edit_balance, target_user_id)
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_edit_subscription_"):
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_edit_subscription_", "")
            bot.send_message(chat_id, f"Введите новую дату окончания подписки для пользователя {target_user_id} (формат: ДД.ММ.ГГГГ ЧЧ:ММ или 'нет' для удаления):")
            bot.register_next_step_handler(call.message, process_edit_subscription, target_user_id)
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_view_user_configs_"):
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_view_user_configs_", "")
            user_info = users_db.get(target_user_id, {})
            used_configs = user_info.get('used_configs', [])
            
            if used_configs:
                message_text = f"**Конфиги пользователя {user_info.get('first_name', 'N/A')} (@{user_info.get('username', 'N/A') or 'N/A'}):**\n\n"
                for i, config in enumerate(used_configs, 1):
                    message_text += f"{i}. **{config['config_name']}**\n"
                    message_text += f"   Период: {get_period_name_ru(config['period'])}\n"
                    message_text += f"   Выдан: {config['issue_date']}\n"
                    message_text += f"   Ссылка: {config['config_link']}\n"
                    message_text += f"   ID конфига: `{config.get('id', 'N/A')}`\n\n" # Show unique ID
            else:
                message_text = "❌ У пользователя нет выданных конфигов."
            
            bot.send_message(chat_id, message_text, parse_mode='Markdown')
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_manage_user_configs":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Управление конфигами пользователей:",
                                 chat_id=chat_id, message_id=message_id,
                                 reply_markup=user_configs_management_keyboard())
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_show_user_configs":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            message_text = "**Все выданные конфиги:**\n\n"
            config_count = 0
            
            # Split into multiple messages if too long
            messages_to_send = []
            current_message_part = message_text

            for uid, user_data in users_db.items():
                used_configs = user_data.get('used_configs', [])
                if used_configs:
                    user_header = f"👤 **Пользователь:** {user_data.get('first_name', 'N/A')} (@{user_data.get('username', 'N/A') or 'N/A'}) ID: {uid}\n"
                    if len(current_message_part) + len(user_header) > 4000: # Telegram limit approx 4096
                        messages_to_send.append(current_message_part)
                        current_message_part = user_header
                    else:
                        current_message_part += user_header

                    for i, config in enumerate(used_configs, 1):
                        config_count += 1
                        config_details = f"  {i}. {config['config_name']} ({get_period_name_ru(config['period'])})\n" \
                                         f"     Ссылка: {config['config_link']}\n" \
                                         f"     Выдан: {config['issue_date']}\n" \
                                         f"     ID конфига: `{config.get('id', 'N/A')}`\n\n"
                        
                        if len(current_message_part) + len(config_details) > 4000:
                            messages_to_send.append(current_message_part)
                            current_message_part = config_details
                        else:
                            current_message_part += config_details
            
            if current_message_part: # Add remaining part
                messages_to_send.append(current_message_part)

            if config_count == 0:
                bot.send_message(chat_id, "❌ Нет выданных конфигов.", reply_markup=user_configs_management_keyboard())
            else:
                for msg in messages_to_send:
                    bot.send_message(chat_id, msg, parse_mode='Markdown')
                bot.send_message(chat_id, "👆 Конец списка выданных конфигов.", reply_markup=user_configs_management_keyboard())
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_delete_user_config":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(chat_id, "Введите ID пользователя и ID конфига для удаления (используйте `/admin_view_user_configs_USER_ID` для получения ID конфига):")
            bot.register_next_step_handler(call.message, process_delete_user_config)
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_reissue_config":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(chat_id, "Введите ID пользователя для перевыдачи конфига:")
            bot.register_next_step_handler(call.message, process_reissue_config)
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

    elif call.data == "admin_broadcast":
        bot.answer_callback_query(call.id)
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(chat_id, "Введите сообщение для рассылки всем пользователям:")
            bot.register_next_step_handler(call.message, process_broadcast_message)
        else:
            bot.send_message(chat_id, "У вас нет прав администратора.")

@bot.message_handler(commands=['manage'])
@admin_only
def handle_manage_command(message):
    try:
        parts = message.text.split('_')
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /manage_USER_ID")
            return

        user_id = parts[1]
        if user_id in users_db:
            user_info = users_db[user_id]
            sub_status = "❌ Нет подписки"
            if user_info.get('subscription_end'):
                sub_end = datetime.datetime.strptime(user_info['subscription_end'], '%Y-%m-%d %H:%M:%S')
                if sub_end > datetime.datetime.now():
                    sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y %H:%M')}"
                else:
                    sub_status = "❌ Истекла"
            
            message_text = f"👤 **Управление пользователем:**\n\n"
            message_text += f"**Имя:** {user_info.get('first_name', 'N/A')}\n"
            message_text += f"**Username:** @{user_info.get('username', 'N/A') or 'N/A'}\n"
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

@bot.message_handler(commands=['review_payment'])
@admin_only
def handle_review_payment_command(message):
    try:
        parts = message.text.split('_')
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /review_payment_PAYMENT_ID")
            return
        
        payment_id = parts[1]
        if payment_id in payments_db and payments_db[payment_id]['status'] == 'pending':
            p_data = payments_db[payment_id]
            user_payment_info = users_db.get(p_data['user_id'])
            username_str = user_payment_info.get('username', 'N/A') if user_payment_info else 'N/A'
            
            bot.send_photo(message.chat.id, p_data['screenshot_id'], 
                           caption=f"Платеж ID: `{payment_id}`\n"
                                   f"От: @{username_str} (ID: {p_data['user_id']})\n"
                                   f"Сумма: {p_data['amount']} ₽\n"
                                   f"Период: {get_period_name_ru(p_data['period'])}\n"
                                   f"Время: {p_data['timestamp']}",
                           parse_mode='Markdown',
                           reply_markup=confirm_payments_keyboard(payment_id))
        else:
            bot.send_message(message.chat.id, "❌ Платеж не найден или уже обработан.")
    except IndexError:
        bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /review_payment_PAYMENT_ID")


@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    user_id = str(message.from_user.id)
    payment_info = message.successful_payment
    
    payload_parts = payment_info.invoice_payload.split('_')
    if len(payload_parts) >= 4:
        period_data = payload_parts[2] + '_' + payload_parts[3]
        
        # Check config availability again before confirming, though it was checked before invoice
        temp_config_check = get_available_config(period_data)
        if not temp_config_check:
            bot.send_message(user_id, f"❌ Оплата прошла успешно, но нет доступных конфигов на {get_period_name_ru(period_data)}.\n"
                                      f"Пожалуйста, свяжитесь с поддержкой для выдачи конфига: @Gl1ch555",
                                      reply_markup=main_menu_keyboard(user_id))
            bot.send_message(ADMIN_ID, f"⚠️ Проблема с успешным Stars платежом от @{message.from_user.username or 'N/A'} (ID: {user_id}). "
                                     f"Оплата прошла, но нет доступных конфигов на {get_period_name_ru(period_data)}.")
            return

        payment_id = get_payment_id()
        payments_db[payment_id] = {
            'user_id': user_id,
            'amount': payment_info.total_amount / 100 * STARS_TO_RUB, # Convert Stars smallest units to rub estimate
            'status': 'confirmed',
            'screenshot_id': None,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'period': period_data,
            'method': 'stars'
        }
        save_data('payments.json', payments_db)
        
        if user_id in users_db:
            current_end = users_db[user_id].get('subscription_end')
            if current_end:
                current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
            else:
                current_end = datetime.datetime.now()

            add_days = get_period_days(period_data)
            
            new_end = current_end + datetime.timedelta(days=add_days)
            users_db[user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            save_data('users.json', users_db)

            user_info = users_db[user_id]
            success, result = send_config_to_user(user_id, period_data, 
                                                user_info.get('username', 'user'), 
                                                user_info.get('first_name', 'User'))
            
            if success:
                bot.send_message(user_id, 
                                 f"✅ Ваш платеж за подписку на {get_period_name_ru(period_data)} подтвержден!\n"
                                 f"⭐ Оплачено: {payment_info.total_amount / 100} Stars\n"
                                 f"📅 Ваша подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                 f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                 reply_markup=main_menu_keyboard(user_id))
            else:
                bot.send_message(user_id, 
                                 f"✅ Платеж подтвержден, но возникла ошибка при выдаче конфига: {result}\n"
                                 f"Обратитесь в поддержку: @Gl1ch555")
        
        bot.send_message(ADMIN_ID, 
                         f"✅ Успешная оплата Stars: {payment_info.total_amount / 100} Stars\n"
                         f"От: @{message.from_user.username or 'N/A'} (ID: {user_id})\n"
                         f"Период: {get_period_name_ru(period_data)}")

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = str(message.from_user.id)
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
        
        user_info = users_db.get(user_id, {})
        username_str = user_info.get('username', 'N/A')
        
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                       caption=f"❗️ Новый скриншот платежа ID: `{pending_payment}`\n"
                               f"От: @{username_str} (ID: {user_id})\n"
                               f"Сумма: {payments_db[pending_payment]['amount']} ₽\n"
                               f"Период: {get_period_name_ru(payments_db[pending_payment]['period'])}\n"
                               f"Время: {payments_db[pending_payment]['timestamp']}",
                       parse_mode='Markdown',
                       reply_markup=confirm_payments_keyboard(pending_payment))

@admin_only
def process_add_configs_bulk(message, period):
    if period not in configs_db:
        configs_db[period] = []
    
    links = message.text.strip().split('\n')
    added_count = 0
    
    for link in links:
        link = link.strip()
        if link and link.startswith(('http://', 'https://')):
            username = message.from_user.username if message.from_user.username else 'admin'
            config_name = f"admin_{message.from_user.id}_{len(configs_db[period]) + 1}" # More robust naming
            
            config_data = {
                'name': config_name,
                'code': f"{username}_{len(configs_db[period]) + 1}",
                'link': link,
                'added_by': username,
                'used': False
            }
            
            configs_db[period].append(config_data)
            added_count += 1
    
    save_data('configs.json', configs_db)
    bot.send_message(message.chat.id, f"✅ Добавлено {added_count} конфигов для периода {get_period_name_ru(period)}.", 
                     reply_markup=manage_configs_keyboard())

@admin_only
def process_delete_config(message):
    try:
        parts = message.text.strip().split()
        period = parts[0]
        config_id_index = int(parts[1]) - 1 # -1 because user inputs starting from 1
        
        if period in configs_db and 0 <= config_id_index < len(configs_db[period]):
            deleted_config = configs_db[period].pop(config_id_index)
            save_data('configs.json', configs_db)
            bot.send_message(message.chat.id, f"✅ Конфиг '{deleted_config['name']}' удален из периода {get_period_name_ru(period)}.")
        else:
            bot.send_message(message.chat.id, "❌ Неверный период или ID конфига. Пожалуйста, убедитесь, что ввели правильный период и числовой ID из списка.")
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: `период ID` (например, `1_month 1`). ID начинаются с 1. Используйте `/admin_show_configs` чтобы увидеть ID.", parse_mode='Markdown')

@admin_only
def process_search_user(message):
    search_term = message.text.strip()
    found_users = []
    
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
                    sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y')}"
                else:
                    sub_status = "❌ Истекла"
            
            message_text += f"👤 **{user_data.get('first_name', 'N/A')}** (@{user_data.get('username', 'N/A') or 'N/A'})\n"
            message_text += f"🆔 ID: `{uid}`\n"
            message_text += f"📊 {sub_status} | 💰 {user_data.get('balance', 0)} ₽\n"
            message_text += f"⚡ /manage_{uid}\n\n"
        
        bot.send_message(message.chat.id, message_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Пользователи не найдены.")

@admin_only
def process_edit_user_id(message):
    target_user_id = message.text.strip()
    if target_user_id in users_db:
        user_info = users_db[target_user_id]
        sub_status = "❌ Нет подписки"
        if user_info.get('subscription_end'):
            sub_end = datetime.datetime.strptime(user_info['subscription_end'], '%Y-%m-%d %H:%M:%S')
            if sub_end > datetime.datetime.now():
                sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y %H:%M')}"
            else:
                sub_status = "❌ Истекла"
        
        message_text = f"👤 **Редактирование пользователя:**\n\n"
        message_text += f"**Имя:** {user_info.get('first_name', 'N/A')}\n"
        message_text += f"**Username:** @{user_info.get('username', 'N/A') or 'N/A'}\n"
        message_text += f"**ID:** `{target_user_id}`\n"
        message_text += f"**Баланс:** {user_info.get('balance', 0)} ₽\n"
        message_text += f"**Подписка:** {sub_status}\n"
        
        bot.send_message(message.chat.id, message_text, 
                       reply_markup=user_action_keyboard(target_user_id),
                       parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Пользователь не найден.")

@admin_only
def process_edit_balance(message, target_user_id):
    try:
        new_balance = int(message.text.strip())
        old_balance = users_db[target_user_id].get('balance', 0)
        users_db[target_user_id]['balance'] = new_balance
        save_data('users.json', users_db)
        
        bot.send_message(message.chat.id, 
                        f"✅ Баланс пользователя {target_user_id} изменен:\n"
                        f"С {old_balance} ₽ на {new_balance} ₽")
        
        bot.send_message(target_user_id, 
                        f"💰 Администратор изменил ваш баланс.\n"
                        f"Новый баланс: {new_balance} ₽")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат баланса. Введите число.")

@admin_only
def process_edit_subscription(message, target_user_id):
    new_subscription = message.text.strip()
    if new_subscription.lower() == 'нет':
        users_db[target_user_id]['subscription_end'] = None
        save_data('users.json', users_db)
        
        bot.send_message(message.chat.id, f"✅ Подписка пользователя {target_user_id} удалена.")
        bot.send_message(target_user_id, "❌ Ваша подписка была удалена администратором.")
    else:
        try:
            new_end = datetime.datetime.strptime(new_subscription, '%d.%m.%Y %H:%M')
            users_db[target_user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            save_data('users.json', users_db)
            
            bot.send_message(message.chat.id, 
                            f"✅ Подписка пользователя {target_user_id} установлена до {new_end.strftime('%d.%m.%Y %H:%M')}.")
            bot.send_message(target_user_id, 
                            f"✅ Администратор изменил срок вашей подписки.\n"
                            f"Новая дата окончания: {new_end.strftime('%d.%m.%Y %H:%M')}")
        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверный формат даты. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")

@admin_only
def process_delete_user_config(message):
    try:
        parts = message.text.strip().split()
        user_id = parts[0]
        config_unique_id = parts[1] # Now expects unique ID, not index
        
        if user_id in users_db:
            used_configs = users_db[user_id].get('used_configs', [])
            found_config_index = -1
            deleted_config = None

            for i, config in enumerate(used_configs):
                if config.get('id') == config_unique_id:
                    found_config_index = i
                    deleted_config = config
                    break

            if found_config_index != -1:
                used_configs.pop(found_config_index)
                users_db[user_id]['used_configs'] = used_configs
                save_data('users.json', users_db)
                
                bot.send_message(message.chat.id, 
                                f"✅ Конфиг пользователя {user_id} удален:\n"
                                f"Имя: {deleted_config['config_name']}\n"
                                f"Период: {get_period_name_ru(deleted_config['period'])}")
                
                bot.send_message(user_id, 
                                f"❌ Ваш конфиг '{deleted_config['config_name']}' был удален администратором.")
            else:
                bot.send_message(message.chat.id, "❌ Конфиг с таким ID не найден у этого пользователя.")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: `ID_пользователя ID_конфига`")

@admin_only
def process_reissue_config(message):
    try:
        user_id = message.text.strip()
        if user_id in users_db:
            user_info = users_db[user_id]
            bot.send_message(message.chat.id, 
                            f"Пользователь: {user_info.get('first_name', 'N/A')} (@{user_info.get('username', 'N/A') or 'N/A'})\n"
                            f"Введите период для перевыдачи конфига (1_month, 2_months, 3_months):")
            bot.register_next_step_handler(message, process_reissue_period, user_id)
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

@admin_only
def process_reissue_period(message, user_id):
    period = message.text.strip()
    if period in PERIOD_INFO: # Check if period is valid
        user_info = users_db[user_id]
        success, result = send_config_to_user(user_id, period, 
                                            user_info.get('username', 'user'), 
                                            user_info.get('first_name', 'User'))
        
        if success:
            bot.send_message(message.chat.id, f"✅ Конфиг успешно перевыдан пользователю {user_id}")
            bot.send_message(user_id, f"✅ Администратор перевыдал вам конфиг на период {get_period_name_ru(period)}. Проверьте сообщения выше.")
        else:
            bot.send_message(message.chat.id, f"❌ Ошибка при перевыдаче: {result}")
    else:
        bot.send_message(message.chat.id, "❌ Неверный период. Используйте: 1_month, 2_months, 3_months")

@admin_only
def process_broadcast_message(message):
    broadcast_text = message.text
    sent_count = 0
    failed_count = 0
    
    bot.send_message(message.chat.id, "📢 Начинаю рассылку. Это может занять некоторое время...")
    
    for uid in users_db.keys():
        try:
            bot.send_message(uid, f"📢 **Объявление от администратора:**\n\n{broadcast_text}", parse_mode='Markdown')
            sent_count += 1
            time.sleep(0.3) # Increased delay to reduce risk of hitting Telegram limits
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {uid}: {e}")
            failed_count += 1
    
    bot.send_message(message.chat.id, 
                    f"✅ Рассылка завершена!\n"
                    f"📤 Отправлено: {sent_count}\n"
                    f"❌ Не отправлено: {failed_count}",
                    reply_markup=admin_keyboard())

def signal_handler(signum, frame):
    print(f"Получен сигнал {signum}. Корректно останавливаю бота...")
    bot.stop_polling()
    print("Бот остановлен.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    print("Бот запускается...")
    # Check if ADMIN_ID is still default and warn
    if ADMIN_ID == 8320218178: # Replace with your actual default ID from the provided code
        print("Внимание: ADMIN_ID не изменен. Пожалуйста, замените его на ваш фактический ID в файле или через переменную окружения.")
    if TOKEN == 'YOUR_DEFAULT_TOKEN_HERE':
        print("Внимание: BOT_TOKEN не изменен. Пожалуйста, замените его на ваш фактический токен в файле или через переменную окружения.")

    try:
        bot.polling(none_stop=True, interval=0, timeout=60)
    except KeyboardInterrupt:
        print("Бот остановлен пользователем (Ctrl+C).")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        # Consider a more robust error handling and logging here.
        # If running with systemd, it might restart.
        print("Бот завершил работу из-за ошибки.")
