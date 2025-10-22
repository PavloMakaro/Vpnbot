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

# === ТОКЕНЫ И КОНФИГУРАЦИЯ ===
TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY'
ADMIN_USERNAME = '@Gl1ch555'
ADMIN_ID = 8320218178  # ← Замените на ваш реальный ID!

# === ЮKASSA ===
PROVIDER_TOKEN = "390540012:LIVE:80557"
CURRENCY = "RUB"

SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
}

REFERRAL_BONUS_NEW_USER = 50
REFERRAL_BONUS_REFERRER = 25
REFERRAL_BONUS_DAYS = 7

bot = telebot.TeleBot(TOKEN)
MAINTENANCE_MODE = False

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def generate_payment_id():
    return str(int(time.time() * 100000))

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

# === ЧЕК ДЛЯ 54-ФЗ ===
def get_provider_data(amount_rub: float, description: str = "Пополнение баланса"):
    return json.dumps({
        "receipt": {
            "items": [
                {
                    "description": description[:128],
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{amount_rub:.2f}",
                        "currency": CURRENCY
                    },
                    "vat_code": 1
                }
            ]
        }
    })

# === ЗАГРУЗКА ДАННЫХ ===
users_db = load_data('users.json')
configs_db = load_data('configs.json')
payments_db = load_data('payments.json')

# === КЛАВИАТУРЫ ===
def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Управление конфигами", callback_data="admin_manage_configs"),
        types.InlineKeyboardButton("Управление пользователями", callback_data="admin_manage_users"),
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
        types.InlineKeyboardButton("Пополнить баланс 💰", callback_data="deposit"),
        types.InlineKeyboardButton("Купить подписку 🚀", callback_data="buy_subscription"),
        types.InlineKeyboardButton("Личный кабинет 👤", callback_data="my_account"),
        types.InlineKeyboardButton("Реферальная система 🤝", callback_data="referral_system")
    )
    if str(user_id) == str(ADMIN_ID):
        markup.add(types.InlineKeyboardButton("Админ-панель 🛠️", callback_data="admin_panel"))
    return markup

def deposit_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    amounts = [50, 100, 200, 500, 1000]
    for amount in amounts:
        markup.add(types.InlineKeyboardButton(f"{amount} ₽", callback_data=f"deposit_{amount}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
    return markup

def buy_subscription_keyboard(user_balance):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for period_key, period_data in SUBSCRIPTION_PERIODS.items():
        price = period_data['price']
        days = period_data['days']
        can_buy = "✅" if user_balance >= price else "❌"
        markup.add(types.InlineKeyboardButton(
            f"{can_buy} {days} дней ({price} ₽)", 
            callback_data=f"buy_sub_{period_key}"
        ))
    markup.add(types.InlineKeyboardButton("Пополнить баланс", callback_data="deposit"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
    return markup

def my_account_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Мои конфиги", callback_data="my_configs"),
        types.InlineKeyboardButton("Пополнить баланс", callback_data="deposit"),
        types.InlineKeyboardButton("Купить подписку", callback_data="buy_subscription"),
        types.InlineKeyboardButton("Назад", callback_data="main_menu")
    )
    return markup

def my_configs_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    user_info = users_db.get(str(user_id), {})
    subscription_end = user_info.get('subscription_end')
    has_active_subscription = False
    if subscription_end:
        end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
        if end_date > datetime.datetime.now():
            has_active_subscription = True
    
    if has_active_subscription:
        markup.add(types.InlineKeyboardButton("Получить конфиг на 30 дней", callback_data="get_config_1_month"))
        markup.add(types.InlineKeyboardButton("Получить конфиг на 60 дней", callback_data="get_config_2_months"))
        markup.add(types.InlineKeyboardButton("Получить конфиг на 90 дней", callback_data="get_config_3_months"))
    else:
        markup.add(types.InlineKeyboardButton("Купить подписку для получения конфига", callback_data="buy_subscription"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="my_account"))
    return markup

# === ВЫДАЧА КОНФИГА ===
def send_config_to_user(user_id, period, username, first_name):
    config = get_available_config(period)
    if not config:
        return False, "Нет доступных конфигов для этого периода"
    mark_config_used(period, config['link'])
    config_name = f"{first_name} ({username}) - {SUBSCRIPTION_PERIODS[period]['days']} дней"
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
    try:
        bot.send_message(user_id, f"🔐 **Ваш VPN конфиг**\n"
                                 f"👤 **Имя:** {config_name}\n"
                                 f"📅 **Период:** {SUBSCRIPTION_PERIODS[period]['days']} дней\n"
                                 f"🔗 **Ссылка на конфиг:** {config['link']}\n"
                                 f"💾 _Сохраните этот конфиг для использования_",
                         parse_mode='Markdown')
        return True, config
    except Exception as e:
        print(f"Error sending config to user {user_id}: {e}")
        return False, f"Ошибка отправки конфига: {e}"

# === ОБРАБОТЧИКИ ===
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
                    users_db[potential_referrer_id]['referrals_count'] = users_db[potential_referrer_id].get('referrals_count', 0) + 1
                    users_db[potential_referrer_id]['balance'] = users_db[potential_referrer_id].get('balance', 0) + REFERRAL_BONUS_REFERRER
                    current_end = users_db[potential_referrer_id].get('subscription_end')
                    if current_end:
                        current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
                    else:
                        current_end = datetime.datetime.now()
                    new_end = current_end + datetime.timedelta(days=REFERRAL_BONUS_DAYS)
                    users_db[potential_referrer_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
                    bot.send_message(potential_referrer_id,
                                     f"🎉 Ваш реферал @{username} зарегистрировался по вашей ссылке! "
                                     f"Вам начислено {REFERRAL_BONUS_REFERRER} ₽ на баланс и {REFERRAL_BONUS_DAYS} дней к подписке!")
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
        welcome_text = f"Привет! Добро пожаловать в VPN Bot!\n🎁 Вам начислен приветственный бонус: {REFERRAL_BONUS_NEW_USER} ₽ на баланс!"
        if referred_by_id:
            welcome_text += f"\n🤝 Вы зарегистрировались по реферальной ссылке!"
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu_keyboard(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "Привет! С возвращением в VPN Bot!", reply_markup=main_menu_keyboard(message.from_user.id))

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

# === CALLBACK ОБРАБОТЧИКИ ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    if MAINTENANCE_MODE and user_id != str(ADMIN_ID):
        bot.answer_callback_query(call.id, "Бот находится на техническом обслуживании. Пожалуйста, попробуйте позже.")
        return

    if call.data == "main_menu":
        bot.edit_message_text("Главное меню:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=main_menu_keyboard(user_id))
    
    # === ПОПОЛНЕНИЕ БАЛАНСА ===
    elif call.data == "deposit":
        bot.edit_message_text("💰 **Пополнение баланса**\n\nВыберите сумму для пополнения:",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown',
                              reply_markup=deposit_keyboard())
    
    elif call.data.startswith("deposit_"):
        amount = int(call.data.replace("deposit_", ""))
        
        prices = [types.LabeledPrice(label=f"Пополнение баланса на {amount} ₽", amount=amount * 100)]
        provider_data = get_provider_data(amount, f"Пополнение баланса на {amount} ₽")

        bot.send_invoice(
            chat_id=call.message.chat.id,
            title="Пополнение баланса",
            description=f"Пополнение баланса на {amount} ₽",
            invoice_payload=f"deposit_{amount}",
            provider_token=PROVIDER_TOKEN,
            currency=CURRENCY,
            prices=prices,
            need_phone_number=True,
            send_phone_number_to_provider=True,
            provider_data=provider_data,
            start_parameter="deposit_balance"
        )
        bot.answer_callback_query(call.id)
    
    # === ПОКУПКА ПОДПИСКИ ===
    elif call.data == "buy_subscription":
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        bot.edit_message_text(f"🚀 **Покупка подписки**\n\n"
                             f"💰 Ваш баланс: {user_balance} ₽\n\n"
                             f"Выберите период подписки:",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown',
                              reply_markup=buy_subscription_keyboard(user_balance))
    
    elif call.data.startswith("buy_sub_"):
        period_key = call.data.replace("buy_sub_", "")
        price = SUBSCRIPTION_PERIODS[period_key]['price']
        days = SUBSCRIPTION_PERIODS[period_key]['days']
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        
        if user_balance < price:
            bot.answer_callback_query(call.id, f"❌ Недостаточно средств! Нужно {price} ₽, на балансе {user_balance} ₽", show_alert=True)
            return
        
        # Списание средств и активация подписки
        users_db[user_id]['balance'] = user_balance - price
        current_end = users_db[user_id].get('subscription_end')
        if current_end:
            current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
        else:
            current_end = datetime.datetime.now()
        new_end = current_end + datetime.timedelta(days=days)
        users_db[user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
        save_data('users.json', users_db)
        
        # Выдача конфига
        user_info = users_db[user_id]
        success, result = send_config_to_user(user_id, period_key,
                                            user_info.get('username', 'user'),
                                            user_info.get('first_name', 'User'))
        
        if success:
            bot.edit_message_text(f"✅ **Подписка активирована!**\n\n"
                                 f"📅 Период: {days} дней\n"
                                 f"💳 Списано: {price} ₽\n"
                                 f"💰 Остаток на балансе: {users_db[user_id]['balance']} ₽\n"
                                 f"📆 Подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n\n"
                                 f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown')
        else:
            bot.edit_message_text(f"✅ **Подписка активирована!**\n\n"
                                 f"📅 Период: {days} дней\n"
                                 f"💳 Списано: {price} ₽\n"
                                 f"💰 Остаток на балансе: {users_db[user_id]['balance']} ₽\n\n"
                                 f"❌ **Ошибка выдачи конфига:** {result}\n"
                                 f"Обратитесь в поддержку: {ADMIN_USERNAME}",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown')
    
    # === ЛИЧНЫЙ КАБИНЕТ ===
    elif call.data == "my_account":
        user_info = users_db.get(user_id, {})
        subscription_end = user_info.get('subscription_end')
        balance = user_info.get('balance', 0)
        days_left = get_subscription_days_left(user_id)
        status_text = "❌ Нет активной подписки"
        if days_left > 0:
            end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
            status_text = f"✅ Активна еще {days_left} дней (до {end_date.strftime('%d.%m.%Y')})"
        bot.edit_message_text(f"👤 **Ваш личный кабинет**\n"
                              f"📊 **Статус подписки:** {status_text}\n"
                              f"💰 **Баланс:** {balance} ₽\n"
                              f"👨 **Ваше имя:** {user_info.get('first_name', 'N/A')}\n"
                              f"📱 **Username:** @{user_info.get('username', 'N/A')}\n"
                              f"🤝 **Рефералов приглашено:** {user_info.get('referrals_count', 0)}\n",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown',
                              reply_markup=my_account_keyboard())
    
    elif call.data == "my_configs":
        bot.edit_message_text("Выберите конфиг для получения (если у вас активна подписка):\n"
                              "❕_Обратите внимание: каждый раз при нажатии кнопки 'Получить конфиг' "
                              "выдается новый уникальный конфиг, если есть свободные._",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown',
                              reply_markup=my_configs_keyboard(user_id))
    
    elif call.data.startswith("get_config_"):
        period_data_key = call.data.replace("get_config_", "")
        user_info = users_db.get(user_id, {})
        days_left = get_subscription_days_left(user_id)
        if days_left <= 0:
            bot.answer_callback_query(call.id, "❌ У вас нет активной подписки или подписка истекла.", show_alert=True)
            bot.edit_message_text("Выберите конфиг для получения (если у вас активна подписки):\n"
                              "❕_Обратите внимание: каждый раз при нажатии кнопки 'Получить конфиг' "
                              "выдается новый уникальный конфиг, если есть свободные._",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown',
                              reply_markup=my_configs_keyboard(user_id))
            return
        success, result = send_config_to_user(user_id, period_data_key,
                                            user_info.get('username', 'user'),
                                            user_info.get('first_name', 'User'))
        if success:
            bot.answer_callback_query(call.id, "✅ Конфиг успешно выдан! Проверьте сообщения.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"❌ {result}", show_alert=True)
    
    elif call.data == "referral_system":
        referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        user_info = users_db.get(user_id, {})
        referrals_count = user_info.get('referrals_count', 0)
        balance = user_info.get('balance', 0)
        bot.edit_message_text(f"🤝 **Реферальная система**\n"
                              f"💡 **Как это работает:**\n"
                              f"• Вы получаете уникальную реферальную ссылку\n"
                              f"• Делитесь ей с друзьями и знакомыми\n"
                              f"• Когда кто-то регистрируется по вашей ссылке:\n"
                              f"  🎁 **Новому пользователю** начисляется {REFERRAL_BONUS_NEW_USER} ₽ на баланс\n"
                              f"  💰 **Вам** начисляется {REFERRAL_BONUS_REFERRER} ₽ на баланс\n"
                              f"  📅 **Вам** добавляется {REFERRAL_BONUS_DAYS} дней к активной подписке\n"
                              f"💰 **Ваши бонусы:**\n"
                              f"• Рефералов приглашено: {referrals_count}\n"
                              f"• Заработано: {referrals_count * REFERRAL_BONUS_REFERRER} ₽\n"
                              f"• Текущий баланс: {balance} ₽\n"
                              f"📎 **Ваша реферальная ссылка:**\n"
                              f"`{referral_link}`\n"
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
                                  reply_markup=main_menu_keyboard(user_id))
    
    # [Остальные админ-функции остаются без изменений]
    elif call.data == "admin_manage_configs":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Управление конфигами:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=manage_configs_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    # [Другие админ-обработчики...]

# === PRE-CHECKOUT И УСПЕШНЫЙ ПЛАТЕЖ ===
@bot.pre_checkout_query_handler(func=lambda query: True)
def handle_pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    user_id = str(message.from_user.id)
    payment = message.successful_payment
    payload = payment.invoice_payload  # "deposit_100"

    try:
        action, amount_str = payload.split('_')
        amount = int(amount_str)
    except Exception as e:
        bot.send_message(user_id, "Ошибка при обработке платежа. Обратитесь в поддержку.")
        bot.send_message(ADMIN_ID, f"Ошибка payload: {payload} от {user_id}")
        return

    if action == "deposit":
        # Пополнение баланса
        current_balance = users_db.get(user_id, {}).get('balance', 0)
        users_db[user_id]['balance'] = current_balance + amount
        save_data('users.json', users_db)

        payment_id = generate_payment_id()
        payments_db[payment_id] = {
            'user_id': user_id,
            'amount': amount,
            'status': 'confirmed',
            'method': 'yookassa',
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': 'deposit'
        }
        save_data('payments.json', payments_db)

        bot.send_message(
            user_id,
            f"✅ **Баланс пополнен!**\n"
            f"💳 Сумма: {amount} ₽\n"
            f"💰 Текущий баланс: {users_db[user_id]['balance']} ₽\n\n"
            f"Теперь вы можете купить подписку!",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard(user_id)
        )

        bot.send_message(
            ADMIN_ID,
            f"✅ Пополнение баланса через ЮKassa:\n"
            f"Пользователь: @{users_db[user_id].get('username', 'N/A')} (ID: {user_id})\n"
            f"Сумма: {amount} ₽\n"
            f"Новый баланс: {users_db[user_id]['balance']} ₽"
        )

# === GRACEFUL SHUTDOWN ===
def signal_handler(signum, frame):
    print(f"Получен сигнал {signum}. Корректно останавливаю бота...")
    bot.stop_polling()
    print("Бот остановлен.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# === ЗАПУСК ===
if __name__ == "__main__":
    print("Бот запускается...")
    if ADMIN_ID == 8320218178:
        print("Внимание: ADMIN_ID не изменен. Пожалуйста, замените его на ваш фактический ID в файле.")
    bot.polling(none_stop=True, interval=0, timeout=60)
