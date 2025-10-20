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
ADMIN_ID = 8320218178 # Пожалуйста, измените этот ID на ваш фактический ID администратора!
CARD_NUMBER = '2204320690808227'
CARD_HOLDER = 'Makarov Pavel Alexandrovich (Ozon Bank)'

SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
}

REFERRAL_BONUS_NEW_USER = 50
REFERRAL_BONUS_REFERRER = 25
REFERRAL_BONUS_DAYS = 7

STARS_TO_RUB = 1.5

bot = telebot.TeleBot(TOKEN)

MAINTENANCE_MODE = False

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

def generate_payment_id():
    return str(int(time.time() * 100000))

def get_available_config(period):
    """Возвращает первый доступный (неиспользованный) конфиг для заданного периода."""
    if period not in configs_db:
        return None
    for config in configs_db[period]:
        if not config.get('used', False):
            return config
    return None

def mark_config_used(period, config_link):
    """Отмечает конфиг как использованный по его ссылке."""
    if period not in configs_db:
        return False
    for config in configs_db[period]:
        if config['link'] == config_link:
            config['used'] = True
            save_data('configs.json', configs_db)
            return True
    return False

def get_subscription_days_left(user_id):
    """Возвращает количество оставшихся дней подписки для пользователя."""
    user_info = users_db.get(str(user_id), {})
    subscription_end = user_info.get('subscription_end')
    if not subscription_end:
        return 0
    try:
        end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return 0 # Некорректный формат даты
    
    now = datetime.datetime.now()
    if end_date <= now:
        return 0
    days_left = (end_date - now).days
    return max(0, days_left)

def get_user_config_for_period(user_id, period):
    """
    Ищет у пользователя уже выданный конфиг для указанного периода.
    Возвращает данные конфига, если найден, иначе None.
    """
    user_info = users_db.get(str(user_id), {})
    used_configs = user_info.get('used_configs', [])
    for config in used_configs:
        if config.get('period') == period:
            return config
    return None

# --- Клавиатуры ---

def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Управление конфигами", callback_data="admin_manage_configs"),
        types.InlineKeyboardButton("Подтвердить платежи", callback_data="admin_confirm_payments"),
        types.InlineKeyboardButton("Управление пользователями", callback_data="admin_manage_users"),
        types.InlineKeyboardButton("Управление конфигами пользователей", callback_data="admin_manage_user_configs"),
        types.InlineKeyboardButton("Рассылка", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("Выйти из админки", callback_data="main_menu")
    )
    return markup

def manage_configs_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Добавить конфиг", callback_data="admin_add_config"),
        types.InlineKeyboardButton("Удалить конфиг", callback_data="admin_delete_config"),
        types.InlineKeyboardButton("Показать конфиги", callback_data="admin_show_configs"),
        types.InlineKeyboardButton("Сбросить использование конфигов", callback_data="admin_reset_configs"),
        types.InlineKeyboardButton("Назад в админ-панель", callback_data="admin_panel")
    )
    return markup

def choose_period_keyboard(action, back_callback="admin_manage_configs"):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for period_key, period_data in SUBSCRIPTION_PERIODS.items():
        markup.add(types.InlineKeyboardButton(f"{period_data['days']} дней", callback_data=f"{action}_{period_key}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data=back_callback))
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
        types.InlineKeyboardButton("Перевыдать конфиг", callback_data="admin_reissue_config_start"),
        types.InlineKeyboardButton("Назад в админ-панель", callback_data="admin_panel")
    )
    return markup

def users_management_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Активные пользователи", callback_data="admin_active_users"),
        types.InlineKeyboardButton("Все пользователи", callback_data="admin_all_users"),
        types.InlineKeyboardButton("Поиск пользователя", callback_data="admin_search_user"),
        types.InlineKeyboardButton("Изменить баланс/подписку", callback_data="admin_edit_user_start"),
        types.InlineKeyboardButton("Назад в админ-панель", callback_data="admin_panel")
    )
    return markup

def user_action_keyboard(target_user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Изменить баланс", callback_data=f"admin_edit_balance_{target_user_id}"),
        types.InlineKeyboardButton("Изменить подписку", callback_data=f"admin_edit_subscription_{target_user_id}"),
        types.InlineKeyboardButton("Просмотреть конфиги", callback_data=f"admin_view_user_configs_{target_user_id}"),
        types.InlineKeyboardButton("Назад к управлению пользователями", callback_data="admin_manage_users")
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
    for period_key, period_data in SUBSCRIPTION_PERIODS.items():
        markup.add(types.InlineKeyboardButton(f"{period_data['days']} дней ({period_data['price']} ₽)", callback_data=f"choose_period_{period_key}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
    return markup

def payment_methods_keyboard(period_callback_data, amount, user_balance, partial_payment_done=False):
    stars_amount = int(amount / STARS_TO_RUB)
    markup = types.InlineKeyboardMarkup(row_width=1)

    if not partial_payment_done: # Если это не продолжение частичной оплаты
        needed_amount_for_balance = max(0, amount - user_balance)
        if needed_amount_for_balance == 0:
            markup.add(types.InlineKeyboardButton(f"💳 Оплата с баланса ({amount} ₽)", callback_data=f"pay_balance_{period_callback_data}"))
        elif user_balance > 0: # Только если есть что списать с баланса
            markup.add(types.InlineKeyboardButton(f"💳 Оплата с баланса ({user_balance} ₽) + доплатить {needed_amount_for_balance} ₽", 
                                                callback_data=f"pay_balance_partial_{period_callback_data}_{amount}"))

    markup.add(
        types.InlineKeyboardButton(f"💳 Оплата картой ({amount} ₽)", callback_data=f"pay_card_{period_callback_data}_{amount}"),
        types.InlineKeyboardButton(f"⭐ Оплата Telegram Stars ({stars_amount} Stars)", callback_data=f"pay_stars_{period_callback_data}_{amount}"),
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
    
    # Проверяем, есть ли активная подписка
    days_left = get_subscription_days_left(user_id)
    
    if days_left > 0:
        markup.add(types.InlineKeyboardButton("Получить/Перевыдать конфиг на 30 дней", callback_data="get_config_1_month"))
        markup.add(types.InlineKeyboardButton("Получить/Перевыдать конфиг на 60 дней", callback_data="get_config_2_months"))
        markup.add(types.InlineKeyboardButton("Получить/Перевыдать конфиг на 90 дней", callback_data="get_config_3_months"))
    else:
        markup.add(types.InlineKeyboardButton("Купить/Продлить подписку для получения конфига", callback_data="buy_vpn"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="my_account"))
    return markup

# --- Вспомогательные функции ---

def send_config_to_user(user_id, period, username, first_name):
    """
    Отправляет конфиг пользователю. Если конфиг для этого периода уже был выдан,
    отправляет его повторно. Иначе выдает новый.
    """
    user_info = users_db.get(str(user_id), {})
    
    # Сначала ищем, был ли уже выдан конфиг для этого периода
    existing_config_data = get_user_config_for_period(user_id, period)

    if existing_config_data:
        # Конфиг уже был выдан, отправляем его повторно
        config_to_send = existing_config_data
        is_new_config = False
    else:
        # Конфиг не был выдан, ищем новый доступный
        new_config = get_available_config(period)
        if not new_config:
            return False, "Нет доступных конфигов для этого периода"
        
        mark_config_used(period, new_config['link']) # Отмечаем новый конфиг как использованный
        
        config_to_send = {
            'config_name': new_config.get('name', f"Config for {first_name}"),
            'config_link': new_config['link'],
            'config_code': new_config.get('code', new_config['link']), 
            'period': period,
            'issue_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_name': f"{first_name} (@{username})"
        }
        
        if 'used_configs' not in user_info:
            user_info['used_configs'] = []
        user_info['used_configs'].append(config_to_send)
        users_db[str(user_id)] = user_info # Обновляем users_db
        save_data('users.json', users_db)
        is_new_config = True
    
    config_name_display = config_to_send.get('config_name', f"VPN {SUBSCRIPTION_PERIODS[period]['days']} дней")
    
    try:
        message_text = (f"🔐 **Ваш VPN конфиг** " + ("(НОВЫЙ)" if is_new_config else "(повторно выдан)") + "\n\n"
                        f"👤 **Имя:** {config_name_display}\n"
                        f"📅 **Период:** {SUBSCRIPTION_PERIODS[period]['days']} дней\n"
                        f"🔗 **Ссылка на конфиг:** `{config_to_send['config_link']}`\n\n"
                        f"💾 _Сохраните этот конфиг для использования_")
        
        # Отправляем конфиг отдельным сообщением
        bot.send_message(user_id, message_text, parse_mode='Markdown')
        return True, config_to_send
    except Exception as e:
        print(f"Error sending config to user {user_id}: {e}")
        return False, f"Ошибка отправки конфига: {e}"

# --- Обработчики сообщений ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username if message.from_user.username else 'N/A'
    first_name = message.from_user.first_name if message.from_user.first_name else 'N/A'

    if MAINTENANCE_MODE and user_id != str(ADMIN_ID):
        bot.send_message(message.chat.id, "Бот находится на техническом обслуживании. Пожалуйста, попробуйте позже.")
        return

    if user_id not in users_db:
        referred_by_id = None
        if len(message.text.split()) > 1:
            try:
                potential_referrer_id = message.text.split()[1]
                if potential_referrer_id.isdigit() and potential_referrer_id in users_db and potential_referrer_id != user_id:
                    referred_by_id = potential_referrer_id
                    
                    # Бонус рефереру
                    users_db[potential_referrer_id]['referrals_count'] = users_db[potential_referrer_id].get('referrals_count', 0) + 1
                    users_db[potential_referrer_id]['balance'] = users_db[potential_referrer_id].get('balance', 0) + REFERRAL_BONUS_REFERRER
                    
                    current_end = users_db[potential_referrer_id].get('subscription_end')
                    if current_end:
                        current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
                    else:
                        current_end = datetime.datetime.now()
                    
                    new_end = current_end + datetime.timedelta(days=REFERRAL_BONUS_DAYS)
                    users_db[potential_referrer_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
                    
                    referrer_username = users_db[potential_referrer_id].get('username', 'пользователь')
                    bot.send_message(potential_referrer_id, 
                                     f"🎉 Ваш реферал @{username} (ID: `{user_id}`) зарегистрировался по вашей ссылке! "
                                     f"Вам начислено {REFERRAL_BONUS_REFERRER} ₽ на баланс и {REFERRAL_BONUS_DAYS} дней к подписке!",
                                     parse_mode='Markdown')

                    save_data('users.json', users_db)
            except ValueError:
                pass

        users_db[user_id] = {
            'balance': REFERRAL_BONUS_NEW_USER,
            'subscription_end': None,
            'referred_by': referred_by_id,
            'username': username,
            'first_name': first_name,
            'referrals_count': 0,
            'used_configs': []
        }
        save_data('users.json', users_db)
        
        welcome_text = f"Привет! Добро пожаловать в VPN Bot!\n\n🎁 Вам начислен приветственный бонус: {REFERRAL_BONUS_NEW_USER} ₽ на баланс!"
        if referred_by_id:
            welcome_text += f"\n🤝 Вы зарегистрировались по реферальной ссылке!"
        
        bot.send_message(message.chat.id, welcome_text,
                         reply_markup=main_menu_keyboard(message.from_user.id),
                         parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "Привет! С возвращением в VPN Bot!",
                         reply_markup=main_menu_keyboard(message.from_user.id))

@bot.message_handler(commands=['maintenance_on'])
def maintenance_on(message):
    global MAINTENANCE_MODE
    if str(message.from_user.id) == str(ADMIN_ID):
        MAINTENANCE_MODE = True
        bot.send_message(ADMIN_ID, "✅ Режим техобслуживания ВКЛЮЧЕН. Бот отвечает только администратору.")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

@bot.message_handler(commands=['maintenance_off'])
def maintenance_off(message):
    global MAINTENANCE_MODE
    if str(message.from_user.id) == str(ADMIN_ID):
        MAINTENANCE_MODE = False
        bot.send_message(ADMIN_ID, "✅ Режим техобслуживания ВЫКЛЮЧЕН. Бот снова доступен всем пользователям.")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

# --- Обработчики Callback Query ---

# Временное хранилище для состояния админских действий, например, для user_id в процессе перевыдачи.
# В более сложном боте лучше использовать FSM (Finite State Machine).
current_admin_action_data = {} 

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)

    if MAINTENANCE_MODE and user_id != str(ADMIN_ID):
        bot.answer_callback_query(call.id, "Бот находится на техническом обслуживании. Пожалуйста, попробуйте позже.")
        return

    # --- Главное меню и покупка VPN ---
    if call.data == "main_menu":
        bot.edit_message_text("Главное меню:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=main_menu_keyboard(user_id))
    
    elif call.data == "buy_vpn":
        bot.edit_message_text("Выберите срок подписки:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=buy_vpn_keyboard())
    
    elif call.data.startswith("choose_period_"):
        period_data_key = call.data.replace("choose_period_", "")
        amount = SUBSCRIPTION_PERIODS[period_data_key]['price']
        
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        days_left = get_subscription_days_left(user_id)
        
        message_text = f"Вы выбрали подписку на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней.\n"
        message_text += f"💳 К оплате: {amount} ₽\n"
        message_text += f"💰 Ваш баланс: {user_balance} ₽\n"
        
        if days_left > 0:
            message_text += f"📅 Текущая подписка активна еще: {days_left} дней\n"
        
        message_text += f"\nВыберите способ оплаты:"
        
        bot.edit_message_text(message_text, 
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id,
                              reply_markup=payment_methods_keyboard(period_data_key, amount, user_balance))

    elif call.data.startswith("pay_balance_partial_"):
        parts = call.data.split('_')
        period_data_key = parts[3] + '_' + parts[4] # '1_month'
        original_amount = int(parts[5])

        user_info = users_db.get(user_id, {})
        user_balance = user_info.get('balance', 0)

        if user_balance > 0:
            amount_to_pay_from_balance = min(user_balance, original_amount)
            users_db[user_id]['balance'] = user_balance - amount_to_pay_from_balance
            save_data('users.json', users_db)

            remaining_amount = original_amount - amount_to_pay_from_balance

            bot.edit_message_text(f"💳 Частичная оплата с баланса: {amount_to_pay_from_balance} ₽. "
                                  f"Остаток на балансе: {users_db[user_id]['balance']} ₽.\n"
                                  f"К доплате: {remaining_amount} ₽.\n\n"
                                  f"Выберите способ доплаты:",
                                  chat_id=call.message.chat.id, 
                                  message_id=call.message.message_id,
                                  reply_markup=payment_methods_keyboard(period_data_key, remaining_amount, 0, partial_payment_done=True))
        else:
            bot.answer_callback_query(call.id, "У вас нет средств на балансе для частичной оплаты.", show_alert=True)
            # Возвращаем пользователя к выбору способа оплаты с учетом его баланса
            bot.edit_message_text(f"Вы выбрали подписку на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней.\n"
                                  f"💳 К оплате: {original_amount} ₽\n"
                                  f"💰 Ваш баланс: {user_balance} ₽\n"
                                  f"\nВыберите способ оплаты:", 
                                  chat_id=call.message.chat.id, 
                                  message_id=call.message.message_id, 
                                  reply_markup=payment_methods_keyboard(period_data_key, original_amount, user_balance))

    elif call.data.startswith("pay_balance_"):
        period_data_key = call.data.replace("pay_balance_", "")
        amount = SUBSCRIPTION_PERIODS[period_data_key]['price']
        
        user_info = users_db.get(user_id, {})
        user_balance = user_info.get('balance', 0)
        
        if user_balance >= amount:
            users_db[user_id]['balance'] = user_balance - amount
            
            current_end = user_info.get('subscription_end')
            if current_end:
                current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
            else:
                current_end = datetime.datetime.now()

            add_days = SUBSCRIPTION_PERIODS[period_data_key]['days']
            
            new_end = current_end + datetime.timedelta(days=add_days)
            users_db[user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            save_data('users.json', users_db)

            success, result = send_config_to_user(user_id, period_data_key, 
                                                user_info.get('username', 'user'), 
                                                user_info.get('first_name', 'User'))
            
            if success:
                bot.edit_message_text(f"✅ Оплата прошла успешно!\n"
                                      f"💳 Списано с баланса: {amount} ₽\n"
                                      f"💰 Остаток на балансе: {users_db[user_id]['balance']} ₽\n"
                                      f"📅 Подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                      f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                      chat_id=call.message.chat.id, 
                                      message_id=call.message.message_id,
                                      parse_mode='Markdown')
            else:
                bot.edit_message_text(f"✅ Оплата прошла успешно, но возникла ошибка при выдаче конфига: {result}\n"
                                      f"Обратитесь в поддержку: {ADMIN_USERNAME}",
                                      chat_id=call.message.chat.id, 
                                      message_id=call.message.message_id,
                                      parse_mode='Markdown')
        else:
            needed_amount = amount - user_balance
            bot.edit_message_text(f"❌ Недостаточно средств на балансе!\n"
                                  f"💰 Ваш баланс: {user_balance} ₽\n"
                                  f"💳 Требуется: {amount} ₽\n"
                                  f"💸 Не хватает: {needed_amount} ₽\n"
                                  f"Пожалуйста, пополните баланс или выберите другой способ оплаты.",
                                  chat_id=call.message.chat.id, 
                                  message_id=call.message.message_id,
                                  reply_markup=payment_methods_keyboard(period_data_key, amount, user_balance))

    elif call.data.startswith("pay_card_"):
        parts = call.data.split('_')
        period_data_key = parts[2] + '_' + parts[3]
        amount = int(parts[4])
        
        payment_id = generate_payment_id()
        payments_db[payment_id] = {
            'user_id': user_id,
            'amount': amount,
            'status': 'pending',
            'screenshot_id': None,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'period': period_data_key,
            'method': 'card',
            'chat_message_id': call.message.message_id # Сохраняем ID сообщения, чтобы потом его отредактировать
        }
        save_data('payments.json', payments_db)

        bot.edit_message_text(f"Для оплаты {amount} ₽ за подписку на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней:"
                              f"\n\n1. Переведите {amount} ₽ на карту: `{CARD_NUMBER}`"
                              f"\nДержатель: `{CARD_HOLDER}`"
                              f"\n\n2. **ОБЯЗАТЕЛЬНО** отправьте скриншот перевода в этот чат."
                              f"\n\nПосле получения скриншота администратор проверит платеж и подтвердит вашу подписку."
                              f"\n**Ваш платеж может быть подтвержден с задержкой, ожидайте, пожалуйста.**",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown')
        
        user_info = users_db.get(user_id, {})
        username_str = user_info.get('username', 'N/A')
        bot.send_message(ADMIN_ID, 
                         f"🔔 Новый платеж на {amount} ₽ от @{username_str} (ID: `{user_id}`) за {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней. "
                         f"Ожидает скриншот.\n"
                         f"Платеж ID: `{payment_id}`", parse_mode='Markdown')

    elif call.data.startswith("pay_stars_"):
        parts = call.data.split('_')
        period_data_key = parts[2] + '_' + parts[3]
        amount_rub = int(parts[4])
        
        stars_amount = int(amount_rub / STARS_TO_RUB)
        
        try:
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"Подписка на VPN ({SUBSCRIPTION_PERIODS[period_data_key]['days']} дней)",
                description=f"Оплата подписки на VPN на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней",
                invoice_payload=f"stars_payment_{period_data_key}_{amount_rub}", # Payload для successful_payment
                provider_token='', 
                currency='XTR', # Валюта для Stars
                prices=[types.LabeledPrice(label=f"VPN на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней", amount=stars_amount)],
                start_parameter='vpn_stars_purchase',
                is_flexible=False,
                reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="buy_vpn"))
            )
            bot.answer_callback_query(call.id, "Открываю счет для оплаты Telegram Stars.", show_alert=False)

        except Exception as e:
            print(f"Ошибка при создании платежа Stars: {e}")
            bot.answer_callback_query(call.id, f"Ошибка при создании платежа Stars: {e}", show_alert=True)
            bot.edit_message_text(f"Ошибка при создании платежа Stars: {e}\nПожалуйста, используйте оплату картой.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=payment_methods_keyboard(period_data_key, amount_rub, users_db.get(user_id, {}).get('balance', 0)))

    # --- Личный кабинет и конфиги ---
    elif call.data == "my_account":
        user_info = users_db.get(user_id, {})
        balance = user_info.get('balance', 0)
        days_left = get_subscription_days_left(user_id)

        status_text = "❌ Нет активной подписки"
        if days_left > 0:
            subscription_end = user_info.get('subscription_end') 
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
        bot.edit_message_text("Выберите срок подписки для получения/перевыдачи конфига:\n\n"
                              "❕_Если у вас уже был выдан конфиг для данного периода, он будет отправлен повторно._\n"
                              "❕_Если нет — будет выдан новый уникальный конфиг, если есть свободные._",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown',
                              reply_markup=my_configs_keyboard(user_id))

    elif call.data.startswith("get_config_"):
        period_data_key = call.data.replace("get_config_", "")
        user_info = users_db.get(user_id, {})
        
        days_left = get_subscription_days_left(user_id)
        if days_left <= 0:
            bot.answer_callback_query(call.id, "❌ У вас нет активной подписки или подписка истекла. Пожалуйста, продлите подписку.", show_alert=True)
            bot.edit_message_text("Выберите срок подписки для получения/перевыдачи конфига:\n\n"
                                  "❕_Если у вас уже был выдан конфиг для данного периода, он будет отправлен повторно._\n"
                                  "❕_Если нет — будет выдан новый уникальный конфиг, если есть свободные._",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown',
                                  reply_markup=my_configs_keyboard(user_id))
            return
        
        success, result = send_config_to_user(user_id, period_data_key, 
                                            user_info.get('username', 'user'), 
                                            user_info.get('first_name', 'User'))
        
        if success:
            bot.answer_callback_query(call.id, "✅ Конфиг успешно выдан/перевыдан! Проверьте сообщения.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"❌ {result}", show_alert=True)

    # --- Поддержка и реферальная система ---
    elif call.data == "support":
        bot.edit_message_text(f"Для связи с поддержкой напишите {ADMIN_USERNAME}.\n"
                              f"Постараемся ответить как можно скорее.",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown', 
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
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown', reply_markup=main_menu_keyboard(user_id))

    # --- Админ-панель ---
    elif call.data == "admin_panel":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("🛠️ Админ-панель:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
            bot.edit_message_text("Главное меню:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=main_menu_keyboard(user_id)) # Возвращаем в главное меню

    # --- Админ: Управление конфигами ---
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
                period_name = SUBSCRIPTION_PERIODS.get(period, {}).get('days', period)
                message_text += f"**{period_name} дней:**\n"
                if configs_list:
                    available_count = sum(1 for config in configs_list if not config.get('used', False))
                    message_text += f"  Всего: {len(configs_list)}, Доступно: {available_count}\n"
                    for i, config in enumerate(configs_list):
                        status = "✅" if not config.get('used', False) else "❌"
                        message_text += f"  {i+1}. {status} {config.get('name', 'N/A')} - `{config['link']}`\n"
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
            bot.edit_message_text(f"✅ Сброшено использование {reset_count} конфигов.", chat_id=call.message.chat.id, message_id=call.message.message_id,
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
            if period not in SUBSCRIPTION_PERIODS:
                bot.send_message(call.message.chat.id, "❌ Неверный период.", reply_markup=manage_configs_keyboard())
                return
            bot.edit_message_text(f"Добавление конфигов для периода: {SUBSCRIPTION_PERIODS[period]['days']} дней\n\n"
                                 f"Отправьте ссылки на конфиги, каждую с новой строки.\n"
                                 f"Имена будут сгенерированы автоматически на основе username администратора и номера конфига.",
                                 chat_id=call.message.chat.id, message_id=call.message.message_id,
                                 parse_mode='Markdown')
            bot.register_next_step_handler(call.message, process_add_configs_bulk, period)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_delete_config":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Введите период и ID конфига для удаления (например, `1_month 1` для первого конфига на 30 дней, ID начинаются с 1).\n"
                                  "Чтобы посмотреть ID, используйте 'Показать конфиги'.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown', reply_markup=manage_configs_keyboard())
            bot.register_next_step_handler(call.message, process_delete_config)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    # --- Админ: Подтверждение платежей ---
    elif call.data == "admin_confirm_payments":
        if str(user_id) == str(ADMIN_ID):
            pending_payments = {pid: p_data for pid, p_data in payments_db.items() if p_data['status'] == 'pending' and p_data.get('screenshot_id') and p_data['method'] == 'card'}
            
            if not pending_payments:
                bot.edit_message_text("Нет платежей, ожидающих подтверждения со скриншотами.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_keyboard())
                return
            
            # Отправляем каждое фото отдельно
            for payment_id, p_data in pending_payments.items():
                user_payment_info = users_db.get(p_data['user_id'])
                username_str = user_payment_info.get('username', 'N/A') if user_payment_info else 'N/A'
                
                bot.send_photo(ADMIN_ID, p_data['screenshot_id'], 
                               caption=f"Платеж ID: `{payment_id}`\n"
                                       f"От: @{username_str} (ID: `{p_data['user_id']}`)\n"
                                       f"Сумма: {p_data['amount']} ₽\n"
                                       f"Период: {SUBSCRIPTION_PERIODS.get(p_data['period'], {}).get('days', p_data['period'])} дней\n"
                                       f"Время: {p_data['timestamp']}",
                               parse_mode='Markdown', reply_markup=confirm_payments_keyboard(payment_id))
            
            # Отправляем сообщение, чтобы пользователь понимал, что список закончился
            bot.send_message(ADMIN_ID, "👆 Это все платежи со скриншотами, ожидающие подтверждения.", reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_confirm_"):
        if str(user_id) == str(ADMIN_ID):
            payment_id = call.data.replace("admin_confirm_", "")
            if payment_id in payments_db and payments_db[payment_id]['status'] == 'pending':
                payments_db[payment_id]['status'] = 'confirmed'
                
                target_user_id = payments_db[payment_id]['user_id']
                period_data_key = payments_db[payment_id]['period']
                amount = payments_db[payment_id]['amount']
                
                if target_user_id in users_db:
                    current_end = users_db[target_user_id].get('subscription_end')
                    if current_end:
                        current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
                    else:
                        current_end = datetime.datetime.now()

                    add_days = SUBSCRIPTION_PERIODS[period_data_key]['days']
                    
                    new_end = current_end + datetime.timedelta(days=add_days)
                    users_db[target_user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
                    save_data('users.json', users_db)

                    user_info = users_db[target_user_id]
                    success, result = send_config_to_user(target_user_id, period_data_key, 
                                                        user_info.get('username', 'user'), 
                                                        user_info.get('first_name', 'User'))
                    
                    if success:
                        bot.send_message(target_user_id, 
                                         f"✅ Ваш платеж за подписку на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней подтвержден!\n"
                                         f"Ваша подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                         f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                         parse_mode='Markdown', 
                                         reply_markup=main_menu_keyboard(target_user_id))
                    else:
                        bot.send_message(target_user_id, 
                                         f"✅ Платеж подтвержден, но возникла ошибка при выдаче конфига: {result}\n"
                                         f"Обратитесь в поддержку: {ADMIN_USERNAME}",
                                         parse_mode='Markdown', 
                                         reply_markup=main_menu_keyboard(target_user_id))
                
                save_data('payments.json', payments_db)
                # Редактируем сообщение с фото
                bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                         caption=f"{call.message.caption}\n\n✅ Подтвержден администратором.",
                                         reply_markup=None, parse_mode='Markdown')
            else:
                bot.answer_callback_query(call.id, "Платеж уже обработан или не найден.", show_alert=True)
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
                                 f"❌ Ваш платеж (ID: `{payment_id}`) был отклонен администратором. "
                                 f"Пожалуйста, свяжитесь с поддержкой ({ADMIN_USERNAME}) для уточнения.", parse_mode='Markdown',
                                 reply_markup=main_menu_keyboard(target_user_id))
                
                bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                         caption=f"{call.message.caption}\n\n❌ Отклонен администратором.",
                                         reply_markup=None, parse_mode='Markdown')
            else:
                bot.answer_callback_query(call.id, "Платеж уже обработан или не найден.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    # --- Админ: Управление пользователями ---
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
            active_users_list = []
            
            for uid, u_data in users_db.items():
                if u_data.get('subscription_end'):
                    try:
                        sub_end = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                        if sub_end > datetime.datetime.now():
                            active_users_list.append((uid, u_data))
                    except ValueError:
                        pass
            
            if not active_users_list:
                message_text = "❌ Нет активных пользователей."
            else:
                for uid, u_data in active_users_list:
                    referred_by = "Нет"
                    if u_data.get('referred_by'):
                        referrer = users_db.get(u_data['referred_by'], {})
                        referred_by = f"@{referrer.get('username', 'N/A')} (ID: `{u_data['referred_by']}`)"
                    
                    sub_end_date_str = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')

                    message_text += f"👤 **{u_data.get('first_name', 'N/A')}** (@{u_data.get('username', 'N/A')})\n"
                    message_text += f"🆔 ID: `{uid}`\n"
                    message_text += f"💰 Баланс: {u_data.get('balance', 0)} ₽\n"
                    message_text += f"📅 Подписка до: {sub_end_date_str}\n"
                    message_text += f"🤝 Рефералов: {u_data.get('referrals_count', 0)}\n"
                    message_text += f"📎 Приглашен: {referred_by}\n"
                    message_text += f"⚡ Действия: `/manage_{uid}`\n\n"
            
            bot.edit_message_text(message_text, chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                  parse_mode='Markdown', reply_markup=users_management_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_all_users":
        if str(user_id) == str(ADMIN_ID):
            message_text = f"**Все пользователи ({len(users_db)}):**\n\n"
            
            user_entries = []
            for uid, u_data in users_db.items():
                sub_status = "❌ Нет подписки"
                if u_data.get('subscription_end'):
                    try:
                        sub_end = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                        if sub_end > datetime.datetime.now():
                            sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y')}"
                        else:
                            sub_status = "❌ Истекла"
                    except ValueError:
                        sub_status = "❌ Некорректная дата"
                
                user_entries.append(
                    f"👤 **{u_data.get('first_name', 'N/A')}** (@{u_data.get('username', 'N/A')})\n"
                    f"   🆔: `{uid}` | {sub_status}\n"
                    f"   💰: {u_data.get('balance', 0)} ₽ | 🤝: {u_data.get('referrals_count', 0)}\n"
                    f"   ⚡ `/manage_{uid}`\n"
                )
            
            current_chunk = []
            for i, entry in enumerate(user_entries):
                current_chunk.append(entry)
                if (i + 1) % 10 == 0 or (i + 1) == len(user_entries): 
                    chunk_text = message_text + "\n".join(current_chunk)
                    if i + 1 == len(user_entries): 
                         bot.edit_message_text(chunk_text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          parse_mode='Markdown', reply_markup=users_management_keyboard())
                    else: 
                        bot.send_message(call.message.chat.id, chunk_text, parse_mode='Markdown')
                    current_chunk = []

            if not user_entries:
                bot.edit_message_text("❌ Нет зарегистрированных пользователей.", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=users_management_keyboard())

        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_search_user":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Введите username или ID пользователя для поиска:", chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_search_user)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_edit_user_start":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Введите ID пользователя, которого хотите изменить:", chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_edit_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_edit_balance_"):
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_edit_balance_", "")
            bot.edit_message_text(f"Введите новый баланс для пользователя `{target_user_id}`:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='Markdown')
            bot.register_next_step_handler(call.message, process_edit_balance, target_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_edit_subscription_"):
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_edit_subscription_", "")
            bot.edit_message_text(f"Введите новую дату окончания подписки для пользователя `{target_user_id}` (формат: ДД.ММ.ГГГГ ЧЧ:ММ или 'нет' для удаления):", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='Markdown')
            bot.register_next_step_handler(call.message, process_edit_subscription, target_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_view_user_configs_"):
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_view_user_configs_", "")
            user_info = users_db.get(target_user_id, {})
            used_configs = user_info.get('used_configs', [])
            
            if used_configs:
                message_text = f"**Конфиги пользователя {user_info.get('first_name', 'N/A')} (@{user_info.get('username', 'N/A')}) ID: `{target_user_id}`:**\n\n"
                for i, config in enumerate(used_configs, 1):
                    period_name = SUBSCRIPTION_PERIODS.get(config.get('period'), {}).get('days', config.get('period', 'N/A'))
                    message_text += f"{i}. **{config.get('config_name', 'N/A')}**\n"
                    message_text += f"   Период: {period_name} дней\n"
                    message_text += f"   Выдан: {config.get('issue_date', 'N/A')}\n"
                    message_text += f"   Ссылка: `{config.get('config_link', 'N/A')}`\n\n"
            else:
                message_text = f"❌ У пользователя `{target_user_id}` нет выданных конфигов."
            
            bot.edit_message_text(message_text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='Markdown', reply_markup=user_action_keyboard(target_user_id))
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    # --- Админ: Управление конфигами пользователей ---
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
            config_entries = []
            
            for uid, user_data in users_db.items():
                used_configs = user_data.get('used_configs', [])
                if used_configs:
                    user_header = f"👤 **Пользователь:** {user_data.get('first_name', 'N/A')} (@{user_data.get('username', 'N/A')}) ID: `{uid}`\n"
                    for i, config in enumerate(used_configs, 1):
                        period_name = SUBSCRIPTION_PERIODS.get(config.get('period'), {}).get('days', config.get('period', 'N/A'))
                        config_entries.append(
                            f"{user_header}"
                            f"  {i}. {config.get('config_name', 'N/A')} ({period_name} дней)\n"
                            f"     Ссылка: `{config.get('config_link', 'N/A')}`\n"
                            f"     Выдан: {config.get('issue_date', 'N/A')}\n"
                        )
            
            if not config_entries:
                message_text = "❌ Нет выданных конфигов."
            else:
                current_chunk_messages = []
                for i, entry in enumerate(config_entries):
                    current_chunk_messages.append(entry)
                    if (i + 1) % 5 == 0 or (i + 1) == len(config_entries): 
                        chunk_text = message_text + "\n".join(current_chunk_messages)
                        if i + 1 == len(config_entries): 
                            bot.edit_message_text(chunk_text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              parse_mode='Markdown', reply_markup=user_configs_management_keyboard())
                        else: 
                            bot.send_message(call.message.chat.id, chunk_text, parse_mode='Markdown')
                        current_chunk_messages = []


        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_delete_user_config":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Введите ID пользователя и номер конфига для удаления (например, `123456789 1`, номер конфига начинается с 1):\n"
                                  "Чтобы посмотреть номера конфигов пользователя, используйте '/manage ID_пользователя' -> 'Просмотреть конфиги'.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown', reply_markup=user_configs_management_keyboard())
            bot.register_next_step_handler(call.message, process_delete_user_config)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_reissue_config_start":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Введите ID пользователя, которому хотите перевыдать конфиг:",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_reissue_config_get_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    # Обработка выбора периода для перевыдачи после ввода user_id
    elif call.data.startswith("reissue_config_"):
        if str(user_id) == str(ADMIN_ID):
            period_key = call.data.replace("reissue_config_", "")
            
            temp_user_data = current_admin_action_data.get(str(call.message.chat.id))
            if not temp_user_data:
                bot.edit_message_text("❌ Ошибка: данные о пользователе для перевыдачи не найдены. Начните сначала.", 
                                      chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=user_configs_management_keyboard())
                return
            
            target_user_id = temp_user_data.get('target_user_id')

            if not target_user_id or target_user_id not in users_db:
                bot.edit_message_text("❌ Ошибка: ID пользователя не найден для перевыдачи. Начните сначала.", 
                                      chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=user_configs_management_keyboard())
                return
            
            user_info = users_db[target_user_id]
            
            days_left = get_subscription_days_left(target_user_id)
            if days_left <= 0:
                bot.edit_message_text(f"❌ У пользователя `{target_user_id}` нет активной подписки. Перевыдача конфига невозможна.",
                                      chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      parse_mode='Markdown', reply_markup=user_configs_management_keyboard())
                bot.answer_callback_query(call.id, "У пользователя нет активной подписки.", show_alert=True)
                return

            success, result = send_config_to_user(target_user_id, period_key, 
                                                user_info.get('username', 'user'), 
                                                user_info.get('first_name', 'User'))
            
            if success:
                bot.edit_message_text(f"✅ Конфиг успешно перевыдан пользователю `{target_user_id}` на период {SUBSCRIPTION_PERIODS[period_key]['days']} дней. "
                                      f"Проверьте его личные сообщения.", 
                                      chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      parse_mode='Markdown', reply_markup=user_configs_management_keyboard())
                bot.send_message(target_user_id, 
                                 f"✅ Администратор перевыдал вам конфиг на период {SUBSCRIPTION_PERIODS[period_key]['days']} дней. Проверьте сообщения выше.", 
                                 parse_mode='Markdown',
                                 reply_markup=main_menu_keyboard(target_user_id))
            else:
                bot.edit_message_text(f"❌ Ошибка при перевыдаче конфига: {result}", 
                                      chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=user_configs_management_keyboard())
            if str(call.message.chat.id) in current_admin_action_data:
                del current_admin_action_data[str(call.message.chat.id)]
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    # --- Админ: Рассылка ---
    elif call.data == "admin_broadcast":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Введите сообщение для рассылки всем пользователям:",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_broadcast_message)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

# --- Обработчики команд для админа ---

@bot.message_handler(commands=['manage'])
def handle_manage_command(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")
        return
    
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
            
            message_text = f"👤 **Управление пользователем:**\n\n"
            message_text += f"**Имя:** {user_info.get('first_name', 'N/A')}\n"
            message_text += f"**Username:** @{user_info.get('username', 'N/A')}\n"
            message_text += f"**ID:** `{target_user_id}`\n"
            message_text += f"**Баланс:** {user_info.get('balance', 0)} ₽\n"
            message_text += f"**Подписка:** {sub_status}\n"
            message_text += f"**Рефералов:** {user_info.get('referrals_count', 0)}\n"
            message_text += f"**Конфигов выдано:** {len(user_info.get('used_configs', []))}\n"
            
            bot.send_message(message.chat.id, message_text, 
                           reply_markup=user_action_keyboard(target_user_id),
                           parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
    except IndexError:
        bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: `/manage_USER_ID`", parse_mode='Markdown')

# --- Обработчики Stars платежей ---

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    user_id = str(message.from_user.id)
    payment_info = message.successful_payment
    
    payload_parts = payment_info.invoice_payload.split('_')
    
    if len(payload_parts) >= 5 and payload_parts[0] == 'stars' and payload_parts[1] == 'payment':
        period_data_key = payload_parts[2] + '_' + payload_parts[3]
        original_amount_rub = int(payload_parts[4])
        
        payment_id = generate_payment_id()
        payments_db[payment_id] = {
            'user_id': user_id,
            'amount': original_amount_rub,
            'status': 'confirmed',
            'screenshot_id': None,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'period': period_data_key,
            'method': 'stars'
        }
        save_data('payments.json', payments_db)
        
        if user_id in users_db:
            current_end = users_db[user_id].get('subscription_end')
            if current_end:
                current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
            else:
                current_end = datetime.datetime.now()

            add_days = SUBSCRIPTION_PERIODS[period_data_key]['days']
            
            new_end = current_end + datetime.timedelta(days=add_days)
            users_db[user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            save_data('users.json', users_db)

            user_info = users_db[user_id]
            success, result = send_config_to_user(user_id, period_data_key, 
                                                user_info.get('username', 'user'), 
                                                user_info.get('first_name', 'User'))
            
            if success:
                bot.send_message(user_id, 
                                 f"✅ Ваш платеж за подписку на {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней подтвержден!\n"
                                 f"⭐ Оплачено: {payment_info.total_amount} Stars\n"
                                 f"📅 Ваша подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                 f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                 parse_mode='Markdown', 
                                 reply_markup=main_menu_keyboard(user_id))
            else:
                bot.send_message(user_id, 
                                 f"✅ Платеж подтвержден, но возникла ошибка при выдаче конфига: {result}\n"
                                 f"Обратитесь в поддержку: {ADMIN_USERNAME}",
                                 parse_mode='Markdown', 
                                 reply_markup=main_menu_keyboard(user_id))
        
        bot.send_message(ADMIN_ID, 
                         f"✅ Успешная оплата Stars: {payment_info.total_amount} Stars\n"
                         f"На сумму: {original_amount_rub} ₽\n"
                         f"От: @{message.from_user.username} (ID: `{user_id}`)\n"
                         f"Период: {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней",
                         parse_mode='Markdown')

# --- Обработчик скриншотов ---

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = str(message.from_user.id)
    
    if MAINTENANCE_MODE and user_id != str(ADMIN_ID):
        bot.send_message(message.chat.id, "Бот находится на техническом обслуживании. Пожалуйста, попробуйте позже.")
        return

    pending_payment_id = None
    for pid, p_data in payments_db.items():
        if p_data['user_id'] == user_id and p_data['status'] == 'pending' and p_data.get('screenshot_id') is None and p_data['method'] == 'card':
            pending_payment_id = pid
            break
    
    if pending_payment_id:
        payments_db[pending_payment_id]['screenshot_id'] = message.photo[-1].file_id
        save_data('payments.json', payments_db)
        
        bot.send_message(message.chat.id, "Скриншот получен! Ожидайте подтверждения от администратора. "
                                         "Ваш платеж может быть подтвержден с задержкой.",
                                         reply_markup=main_menu_keyboard(user_id)) 
        
        user_info = users_db.get(user_id, {})
        username_str = user_info.get('username', 'N/A')
        
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                       caption=f"❗️ Новый скриншот платежа ID: `{pending_payment_id}`\n"
                               f"От: @{username_str} (ID: `{user_id}`)\n"
                               f"Сумма: {payments_db[pending_payment_id]['amount']} ₽\n"
                               f"Период: {SUBSCRIPTION_PERIODS.get(payments_db[pending_payment_id]['period'], {}).get('days', 'N/A')} дней",
                       parse_mode='Markdown', reply_markup=confirm_payments_keyboard(pending_payment_id))
    else:
        bot.send_message(message.chat.id, "Я не ожидал скриншот платежа. У вас есть незавершенные платежи картой?",
                                         reply_markup=main_menu_keyboard(user_id))

# --- Функции для next_step_handler (Admin) ---

def process_add_configs_bulk(message, period_key):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    if period_key not in configs_db:
        configs_db[period_key] = []
    
    links = message.text.strip().split('\n')
    added_count = 0
    
    for link in links:
        link = link.strip()
        if link and (link.startswith('http://') or link.startswith('https://')):
            if any(config['link'] == link for config in configs_db[period_key]):
                bot.send_message(message.chat.id, f"⚠️ Конфиг с ссылкой `{link}` уже существует в списке, пропущен.", parse_mode='Markdown')
                continue
            
            username = message.from_user.username if message.from_user.username else 'admin'
            config_name = f"{username}_{period_key}_{len(configs_db[period_key]) + 1}"
            
            config_data = {
                'name': config_name,
                'code': config_name, 
                'link': link,
                'added_by': username,
                'used': False
            }
            
            configs_db[period_key].append(config_data)
            added_count += 1
    
    save_data('configs.json', configs_db)
    bot.send_message(message.chat.id, f"✅ Добавлено {added_count} конфигов для периода {SUBSCRIPTION_PERIODS[period_key]['days']} дней.", 
                     reply_markup=manage_configs_keyboard())

def process_delete_config(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            raise ValueError("Неверное количество аргументов")

        period_key = parts[0]
        config_id = int(parts[1]) - 1 
        
        if period_key in SUBSCRIPTION_PERIODS and period_key in configs_db and 0 <= config_id < len(configs_db[period_key]):
            deleted_config = configs_db[period_key].pop(config_id)
            save_data('configs.json', configs_db)
            bot.send_message(message.chat.id, f"✅ Конфиг '{deleted_config.get('name', 'N/A')}' удален из периода {SUBSCRIPTION_PERIODS[period_key]['days']} дней.",
                             reply_markup=manage_configs_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ Неверный период или ID конфига. Пожалуйста, проверьте данные.", reply_markup=manage_configs_keyboard())
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: `период ID` (например, `1_month 1`)", parse_mode='Markdown', reply_markup=manage_configs_keyboard())

def process_search_user(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
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
            message_text += f"📊 {sub_status} | 💰 {user_data.get('balance', 0)} ₽\n"
            message_text += f"⚡ `/manage_{uid}`\n\n"
        
        bot.send_message(message.chat.id, message_text, parse_mode='Markdown', reply_markup=users_management_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Пользователи не найдены.", reply_markup=users_management_keyboard())

def process_edit_user_id(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    target_user_id = message.text.strip()
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
        bot.send_message(message.chat.id, "❌ Пользователь не найден.", reply_markup=users_management_keyboard())

def process_edit_balance(message, target_user_id):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        new_balance = int(message.text.strip())
        old_balance = users_db[target_user_id].get('balance', 0)
        users_db[target_user_id]['balance'] = new_balance
        save_data('users.json', users_db)
        
        bot.send_message(message.chat.id, 
                        f"✅ Баланс пользователя `{target_user_id}` изменен:\n"
                        f"С {old_balance} ₽ на {new_balance} ₽", parse_mode='Markdown', reply_markup=user_action_keyboard(target_user_id))
        
        bot.send_message(target_user_id, 
                        f"💰 Администратор изменил ваш баланс.\n"
                        f"Новый баланс: {new_balance} ₽", parse_mode='Markdown', reply_markup=main_menu_keyboard(target_user_id))
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат баланса. Введите целое число.", reply_markup=user_action_keyboard(target_user_id))

def process_edit_subscription(message, target_user_id):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    new_subscription = message.text.strip()
    if new_subscription.lower() == 'нет':
        users_db[target_user_id]['subscription_end'] = None
        save_data('users.json', users_db)
        
        bot.send_message(message.chat.id, f"✅ Подписка пользователя `{target_user_id}` удалена.", parse_mode='Markdown', reply_markup=user_action_keyboard(target_user_id))
        bot.send_message(target_user_id, "❌ Ваша подписка была удалена администратором.", parse_mode='Markdown', reply_markup=main_menu_keyboard(target_user_id))
    else:
        try:
            new_end = datetime.datetime.strptime(new_subscription, '%d.%m.%Y %H:%M')
            users_db[target_user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            save_data('users.json', users_db)
            
            bot.send_message(message.chat.id, 
                            f"✅ Подписка пользователя `{target_user_id}` установлена до {new_end.strftime('%d.%m.%Y %H:%M')}.", parse_mode='Markdown', reply_markup=user_action_keyboard(target_user_id))
            bot.send_message(target_user_id, 
                            f"✅ Администратор изменил срок вашей подписки.\n"
                            f"Новая дата окончания: {new_end.strftime('%d.%m.%Y %H:%M')}", parse_mode='Markdown', reply_markup=main_menu_keyboard(target_user_id))
        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверный формат даты. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ", reply_markup=user_action_keyboard(target_user_id))

def process_delete_user_config(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            raise ValueError("Неверное количество аргументов")

        user_id = parts[0]
        config_index = int(parts[1]) - 1 
        
        if user_id in users_db:
            used_configs = users_db[user_id].get('used_configs', [])
            if 0 <= config_index < len(used_configs):
                deleted_config = used_configs.pop(config_index)
                users_db[user_id]['used_configs'] = used_configs
                save_data('users.json', users_db)
                
                period_name = SUBSCRIPTION_PERIODS.get(deleted_config.get('period'), {}).get('days', deleted_config.get('period', 'N/A'))
                bot.send_message(message.chat.id, 
                                f"✅ Конфиг пользователя `{user_id}` удален:\n"
                                f"Имя: {deleted_config.get('config_name', 'N/A')}\n"
                                f"Период: {period_name} дней", 
                                parse_mode='Markdown', reply_markup=user_configs_management_keyboard())
                
                bot.send_message(user_id, 
                                f"❌ Ваш конфиг '{deleted_config.get('config_name', 'N/A')}' был удален администратором.", parse_mode='Markdown', reply_markup=main_menu_keyboard(user_id))
            else:
                bot.send_message(message.chat.id, "❌ Неверный номер конфига. Пожалуйста, проверьте и попробуйте снова.", parse_mode='Markdown', reply_markup=user_configs_management_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.", reply_markup=user_configs_management_keyboard())
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: `ID_пользователя номер_конфига`", parse_mode='Markdown', reply_markup=user_configs_management_keyboard())

def process_reissue_config_get_user_id(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    target_user_id = message.text.strip()
    if target_user_id in users_db:
        user_info = users_db[target_user_id]
        current_admin_action_data[str(message.chat.id)] = {'target_user_id': target_user_id}
        
        bot.send_message(message.chat.id, 
                        f"Пользователь: {user_info.get('first_name', 'N/A')} (@{user_info.get('username', 'N/A')})\n"
                        f"Выберите период для перевыдачи конфига:", 
                        parse_mode='Markdown', 
                        reply_markup=choose_period_keyboard("reissue_config", back_callback="admin_manage_user_configs"))
    else:
        bot.send_message(message.chat.id, "❌ Пользователь не найден. Пожалуйста, введите корректный ID.", reply_markup=user_configs_management_keyboard())

def process_broadcast_message(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    broadcast_text = message.text
    sent_count = 0
    failed_count = 0
    
    bot.send_message(message.chat.id, "📢 Начинаю рассылку...")
    
    for uid in users_db.keys():
        try:
            bot.send_message(uid, f"📢 **Объявление от администратора:**\n\n{broadcast_text}", parse_mode='Markdown')
            sent_count += 1
            time.sleep(0.1) 
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {uid}: {e}")
            failed_count += 1
    
    bot.send_message(message.chat.id, 
                    f"✅ Рассылка завершена!\n"
                    f"📤 Отправлено: {sent_count}\n"
                    f"❌ Не отправлено: {failed_count}",
                    reply_markup=admin_keyboard())

# --- graceful shutdown ---
def signal_handler(signum, frame):
    print(f"Получен сигнал {signum}. Корректно останавливаю бота...")
    bot.stop_polling()
    print("Бот остановлен.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    print("Бот запускается...")
    if ADMIN_ID == 8320218178: 
        print("\n" + "="*80)
        print("ВНИМАНИЕ: ADMIN_ID не изменен. Пожалуйста, замените '8320218178' на ваш фактический Telegram ID в коде.")
        print("Без этого админ-панель не будет работать корректно!")
        print("Чтобы узнать свой ID, напишите @userinfobot в Telegram.")
        print("="*80 + "\n")
    try:
        bot.polling(none_stop=True, interval=0, timeout=60)
    except KeyboardInterrupt:
        print("Бот остановлен пользователем (Ctrl+C).")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        print("Бот будет перезапущен, если настроен через systemd.")
