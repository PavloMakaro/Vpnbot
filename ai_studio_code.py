import telebot
from telebot import types
import json
import time
import datetime
import threading
import os
import signal
import sys
import math

class Config:
    TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY'
    ADMIN_USERNAME = '@Gl1ch555'
    ADMIN_ID = 8320218178
    CARD_NUMBER = '2204320690808227'
    CARD_HOLDER = 'Makarov Pavel Alexandrovich (Ozon Bank)'

    PRICES = {
        '1_month': 50,
        '2_months': 90,
        '3_months': 120
    }

    PERIOD_TO_DAYS = {
        '1_month': 30,
        '2_months': 60,
        '3_months': 90
    }

    REFERRAL_BONUS_NEW_USER = 50
    REFERRAL_BONUS_REFERRER = 25
    REFERRAL_BONUS_DAYS = 7

    STARS_TO_RUB = 1.5
    BROADCAST_DELAY_SEC = 0.5

DB_LOCK = threading.Lock()

bot = telebot.TeleBot(Config.TOKEN)

def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Ошибка сохранения данных в {filename}: {e}")

users_db = load_data('users.json')
configs_db = load_data('configs.json')
payments_db = load_data('payments.json')

def get_price_data(period):
    return Config.PRICES.get(period, 0), Config.PERIOD_TO_DAYS.get(period, 0)

def is_admin(user_id):
    return str(user_id) == str(Config.ADMIN_ID)

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📈 Статистика"),
        types.KeyboardButton("👤 Управление пользователями"),
        types.KeyboardButton("⚙️ Управление конфигами"),
        types.KeyboardButton("📢 Рассылка"),
        types.KeyboardButton("💰 Платежи")
    )
    return markup

def user_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💎 Баланс"),
        types.KeyboardButton("🌐 Мои конфиги"),
        types.KeyboardButton("💳 Купить подписку"),
        types.KeyboardButton("🤝 Реферальная система"),
        types.KeyboardButton("👨‍💻 Поддержка")
    )
    return markup

def back_to_admin_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Назад в Админ-панель", callback_data="admin_menu"))
    return markup

def get_subscription_days_left(user_id):
    with DB_LOCK:
        user_data = users_db.get(str(user_id))
        if not user_data or not user_data.get('subscription_end'):
            return 0

        end_date_str = user_data['subscription_end']
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return 0

        now = datetime.datetime.now()
        if end_date <= now:
            return 0

        return (end_date - now).days

def add_subscription_time(user_id, days):
    with DB_LOCK:
        user_id_str = str(user_id)
        if user_id_str not in users_db:
            return

        user_data = users_db[user_id_str]
        current_end_str = user_data.get('subscription_end')

        now = datetime.datetime.now()
        
        if current_end_str:
            try:
                current_end = datetime.datetime.strptime(current_end_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                current_end = now
        else:
            current_end = now

        if current_end <= now:
            new_end = now + datetime.timedelta(days=days)
        else:
            new_end = current_end + datetime.timedelta(days=days)

        user_data['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
        save_data('users.json', users_db)

def send_config_to_user(chat_id, user_id, period):
    period_key = period
    
    with DB_LOCK:
        if not configs_db.get(period_key):
            bot.send_message(chat_id, "❌ Извините, конфиги на этот период закончились. Попробуйте позже или обратитесь в поддержку.")
            return

        config_url = configs_db[period_key].pop(0)
        
        user_data = users_db.get(str(user_id))
        if user_data:
            user_data['config_url'] = config_url
            user_data['config_period'] = period_key
            save_data('users.json', users_db)

        save_data('configs.json', configs_db)
    
    bot.send_message(chat_id, 
                     f"✅ Ваша подписка на **{period.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}** активирована!\n\n"
                     f"🔑 **Ваш конфиг:** {config_url}\n\n"
                     "💡 Если у вас возникли вопросы, обратитесь в поддержку.", 
                     parse_mode='Markdown')

def get_config_period_display(period):
    if period == '1_month': return "1 месяц"
    if period == '2_months': return "2 месяца"
    if period == '3_months': return "3 месяца"
    return period

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = str(message.chat.id)
    referrer_id = None
    
    if len(message.text.split()) > 1:
        try:
            referrer_id = str(int(message.text.split()[1]))
        except ValueError:
            pass
        
    with DB_LOCK:
        if user_id not in users_db:
            users_db[user_id] = {
                'username': message.from_user.username,
                'first_name': message.from_user.first_name,
                'balance': 0,
                'subscription_end': None,
                'referrer_id': None,
                'referral_count': 0,
                'config_url': None,
                'config_period': None,
                'is_banned': False
            }
            
            if referrer_id and referrer_id != user_id and referrer_id in users_db:
                users_db[user_id]['referrer_id'] = referrer_id
                
                # Начисление бонусов
                users_db[referrer_id]['referral_count'] += 1
                users_db[referrer_id]['balance'] += Config.REFERRAL_BONUS_REFERRER
                
                # Добавление времени рефералу (новому пользователю)
                add_subscription_time(user_id, Config.REFERRAL_BONUS_DAYS)
                
                bot.send_message(referrer_id, f"🎁 Новый пользователь! Вам начислено {Config.REFERRAL_BONUS_REFERRER} ₽ на баланс.")
                bot.send_message(message.chat.id, 
                                 f"🎉 Добро пожаловать! Вы зарегистрированы по реферальной ссылке и получили бонус: {Config.REFERRAL_BONUS_DAYS} дней подписки.", 
                                 reply_markup=user_keyboard())
                save_data('users.json', users_db)
                return
            
            save_data('users.json', users_db)

    bot.send_message(message.chat.id, 
                     "🤖 Добро пожаловать! Я бот для продажи VPN-конфигов.", 
                     reply_markup=user_keyboard())

@bot.message_handler(func=lambda message: message.text in ["💎 Баланс", "🌐 Мои конфиги", "💳 Купить подписку", "🤝 Реферальная система", "👨‍💻 Поддержка"])
def handle_user_menu(message):
    user_id = str(message.chat.id)
    
    with DB_LOCK:
        user_data = users_db.get(user_id)
        if not user_data:
            start_message(message)
            return
        
        if user_data.get('is_banned'):
            bot.send_message(user_id, "❌ Ваш аккаунт заблокирован.")
            return

    if message.text == "💎 Баланс":
        with DB_LOCK:
            balance = users_db[user_id]['balance']
        bot.send_message(user_id, f"Ваш текущий баланс: **{balance} ₽**", parse_mode='Markdown')

    elif message.text == "🌐 Мои конфиги":
        days_left = get_subscription_days_left(user_id)
        with DB_LOCK:
            config_url = users_db[user_id].get('config_url')
            config_period = users_db[user_id].get('config_period')

        if days_left > 0:
            markup = types.InlineKeyboardMarkup()
            
            if config_url:
                period_display = get_config_period_display(config_period)
                markup.add(types.InlineKeyboardButton(f"👁️ Посмотреть текущий конфиг ({period_display})", callback_data="show_my_config"))
                markup.add(types.InlineKeyboardButton("🗑️ Сбросить (удалить) текущий конфиг", callback_data="reset_my_config"))
                bot.send_message(user_id, 
                                 f"✅ Ваша подписка активна! Осталось {days_left} дней.\n"
                                 "У вас уже есть активный конфиг. Вы можете посмотреть его или сбросить.", 
                                 reply_markup=markup)
            else:
                markup.add(types.InlineKeyboardButton("🔑 Получить конфиг", callback_data="get_new_config"))
                bot.send_message(user_id, 
                                 f"✅ Ваша подписка активна! Осталось {days_left} дней.\n"
                                 "Вы еще не получали конфиг для этой подписки.", 
                                 reply_markup=markup)
        else:
            bot.send_message(user_id, "❌ У вас нет активной подписки.", reply_markup=buy_keyboard())

    elif message.text == "💳 Купить подписку":
        bot.send_message(user_id, "Выберите период подписки:", reply_markup=buy_keyboard())

    elif message.text == "🤝 Реферальная система":
        with DB_LOCK:
            referral_count = users_db[user_id].get('referral_count', 0)
        
        referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        
        bot.send_message(user_id, 
                         f"🤝 **Ваша реферальная ссылка:**\n`{referral_link}`\n\n"
                         f"👥 Приглашено пользователей: **{referral_count}**\n"
                         f"🎁 Вы получаете **{Config.REFERRAL_BONUS_REFERRER} ₽** за каждого нового пользователя, который зарегистрируется по вашей ссылке.", 
                         parse_mode='Markdown')

    elif message.text == "👨‍💻 Поддержка":
        bot.send_message(user_id, f"По вопросам поддержки пишите администратору: {Config.ADMIN_USERNAME}")

@bot.message_handler(commands=['admin'])
def admin_panel_command(message):
    if is_admin(message.chat.id):
        bot.send_message(message.chat.id, "🔐 **Админ-панель**", reply_markup=admin_keyboard(), parse_mode='Markdown')

def buy_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for period, price in Config.PRICES.items():
        markup.add(types.InlineKeyboardButton(f"Купить на {get_config_period_display(period)} ({price} ₽)", callback_data=f"choose_period_{period}"))
    return markup

def payment_methods_keyboard(period, amount, user_balance):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton(f"⭐️ Оплата Stars (Прием не работает)", callback_data=f"pay_stars_{period}"))
    
    needed_amount = max(0, amount - user_balance)
    
    if user_balance >= amount:
        markup.add(types.InlineKeyboardButton(f"💳 Оплата с баланса ({amount} ₽)", callback_data=f"pay_balance_{period}"))
    else:
        markup.add(types.InlineKeyboardButton(f"❌ Недостаточно средств на балансе. (Не хватает {needed_amount} ₽)", callback_data="no_funds_alert"))
    
    markup.add(types.InlineKeyboardButton(f"💰 Оплата картой ({amount} ₽)", callback_data=f"pay_card_{period}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="buy_subscription_menu"))
    return markup

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.message.chat.id)
    call_data = call.data
    
    if call_data == "admin_menu":
        if is_admin(call.message.chat.id):
            bot.edit_message_text("🔐 **Админ-панель**", call.message.chat.id, call.message.message_id, reply_markup=admin_keyboard(), parse_mode='Markdown')
            bot.answer_callback_query(call.id)
            return
        
    if not is_admin(call.message.chat.id) and call_data.startswith('admin_'):
        bot.answer_callback_query(call.id, "У вас нет прав администратора.")
        return

    if call_data.startswith("choose_period_"):
        period_data = call_data.split("_")[2]
        amount, _ = get_price_data(period_data)
        
        with DB_LOCK:
            user_balance = users_db.get(user_id, {}).get('balance', 0)
        
        bot.edit_message_text(f"Вы выбрали подписку на **{get_config_period_display(period_data)}** за **{amount} ₽**.\nВыберите способ оплаты:", 
                              call.message.chat.id, 
                              call.message.message_id, 
                              reply_markup=payment_methods_keyboard(period_data, amount, user_balance),
                              parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        
    elif call_data == "buy_subscription_menu":
        bot.edit_message_text("Выберите период подписки:", call.message.chat.id, call.message.message_id, reply_markup=buy_keyboard())
        bot.answer_callback_query(call.id)

    elif call_data == "no_funds_alert":
        bot.answer_callback_query(call.id, "Пожалуйста, пополните баланс или выберите другой способ оплаты.")

    elif call_data.startswith("pay_balance_"):
        period_data = call_data.split("_")[2]
        amount, days = get_price_data(period_data)
        
        with DB_LOCK:
            user_data = users_db.get(user_id)
            if not user_data:
                bot.answer_callback_query(call.id, "Ошибка пользователя. Нажмите /start.")
                return

            user_balance = user_data.get('balance', 0)

            if user_balance < amount:
                bot.answer_callback_query(call.id, "❌ Недостаточно средств на балансе.")
                return

            if not configs_db.get(period_data) or not configs_db.get(period_data):
                bot.answer_callback_query(call.id, "❌ Извините, конфиги на этот период закончились.")
                return

            user_data['balance'] -= amount
            save_data('users.json', users_db)

        add_subscription_time(user_id, days)
        send_config_to_user(call.message.chat.id, user_id, period_data)

        bot.edit_message_text(f"✅ Оплата с баланса ({amount} ₽) успешно произведена. Подписка активирована!", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)

    elif call_data.startswith("pay_card_"):
        period_data = call_data.split("_")[2]
        amount, _ = get_price_data(period_data)
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{period_data}_{amount}"))
        
        bot.edit_message_text(f"💳 **Оплата картой**\n\n"
                              f"Сумма: **{amount} ₽**\n"
                              f"Карта: `{Config.CARD_NUMBER}`\n"
                              f"Получатель: `{Config.CARD_HOLDER}`\n\n"
                              f"**Внимание!** Переведите точную сумму и прикрепите скриншот оплаты.", 
                              call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')
        bot.answer_callback_query(call.id)

    elif call_data.startswith("paid_"):
        _, period, amount = call_data.split("_")
        amount = int(amount)
        
        with DB_LOCK:
            payment_id = str(len(payments_db) + 1)
            payments_db[payment_id] = {
                'user_id': user_id,
                'period': period,
                'amount': amount,
                'status': 'pending',
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'screenshot_id': None
            }
            save_data('payments.json', payments_db)

        msg = bot.send_message(call.message.chat.id, 
                         "Отправьте скриншот чека в следующем сообщении, чтобы я мог проверить оплату.")
        bot.register_next_step_handler(msg, process_screenshot, payment_id)
        bot.answer_callback_query(call.id)

    elif call_data.startswith("pay_stars_"):
        period_data = call_data.split("_")[2]
        amount, _ = get_price_data(period_data)
        
        stars_amount = math.ceil(amount / Config.STARS_TO_RUB)
        
        bot.answer_callback_query(call.id, 
                                  f"Оплата Stars сейчас не работает. Требуется {stars_amount} Stars.", 
                                  show_alert=True)
    
    elif call_data == "get_new_config":
        days_left = get_subscription_days_left(user_id)
        if days_left <= 0:
            bot.answer_callback_query(call.id, "❌ У вас нет активной подписки.")
            return

        with DB_LOCK:
            # Находим период с наибольшим количеством дней (3 месяца > 2 месяца > 1 месяц)
            active_period = None
            max_days = 0
            for period, days in Config.PERIOD_TO_DAYS.items():
                if days <= days_left and days > max_days:
                    active_period = period
                    max_days = days
            
            if not active_period:
                bot.answer_callback_query(call.id, "Не удалось определить период. Обратитесь в поддержку.")
                return

        send_config_to_user(call.message.chat.id, user_id, active_period)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "✅ Конфиг успешно выдан.")

    elif call_data == "show_my_config":
        with DB_LOCK:
            config_url = users_db.get(user_id, {}).get('config_url')
        
        if config_url:
            bot.send_message(call.message.chat.id, f"🔑 **Ваш текущий конфиг:**\n`{config_url}`", parse_mode='Markdown')
            bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, "❌ У вас нет активного конфига. Получите его.")

    elif call_data == "reset_my_config":
        with DB_LOCK:
            user_data = users_db.get(user_id)
            if user_data and user_data.get('config_url'):
                user_data['config_url'] = None
                user_data['config_period'] = None
                save_data('users.json', users_db)
                bot.answer_callback_query(call.id, "✅ Ваш конфиг сброшен. Вы можете получить новый.")
                bot.edit_message_text("✅ Ваш конфиг сброшен. Вы можете получить новый.", call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔑 Получить новый конфиг", callback_data="get_new_config")))
            else:
                bot.answer_callback_query(call.id, "❌ У вас нет активного конфига для сброса.")

    elif call_data == "admin_manage_configs":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("➕ Добавить конфиги", callback_data="admin_add_config"))
        keyboard.add(types.InlineKeyboardButton("➖ Удалить конфиг", callback_data="admin_delete_config"))
        keyboard.add(types.InlineKeyboardButton("📊 Статус конфигов", callback_data="admin_configs_status"))
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu"))
        bot.edit_message_text("⚙️ **Управление конфигами**", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')
        bot.answer_callback_query(call.id)

    elif call_data == "admin_configs_status":
        with DB_LOCK:
            status_text = "📊 **Статус конфигов:**\n\n"
            total = 0
            for period, configs in configs_db.items():
                count = len(configs)
                status_text += f"**{get_config_period_display(period)}**: {count} шт.\n"
                total += count
            status_text += f"\n**Общее количество**: {total} шт."
        
        bot.edit_message_text(status_text, call.message.chat.id, call.message.message_id, reply_markup=back_to_admin_keyboard(), parse_mode='Markdown')
        bot.answer_callback_query(call.id)

    elif call_data == "admin_add_config":
        msg = bot.send_message(call.message.chat.id, 
                               "➕ **Добавление конфигов**\n\n"
                               "Введите период и ссылки на конфиги, каждый с новой строки.\n\n"
                               "**Формат:** `[период]`\n`[ссылка1]`\n`[ссылка2]`\n\n"
                               "**Пример:**\n`1_month`\n`https://vpn.link/1`\n`https://vpn.link/2`",
                               parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_add_config)
        bot.answer_callback_query(call.id)

    elif call_data == "admin_delete_config":
        msg = bot.send_message(call.message.chat.id, 
                               "➖ **Удаление конфига**\n\n"
                               "Введите **период** и **ссылку** на конфиг для удаления.\n\n"
                               "**Формат:** `[период] [ссылка]`\n\n"
                               "**Пример:** `1_month https://vpn.link/1`",
                               parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_delete_config)
        bot.answer_callback_query(call.id)

    elif call_data == "admin_manage_users":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔎 Найти/Изменить пользователя", callback_data="admin_find_user"))
        keyboard.add(types.InlineKeyboardButton("🚫 Заблокировать/Разблокировать", callback_data="admin_ban_user"))
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu"))
        bot.edit_message_text("👤 **Управление пользователями**", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    
    elif call_data.startswith("admin_confirm_") or call_data.startswith("admin_reject_"):
        action, payment_id = call_data.split("_")[1:3]
        
        with DB_LOCK:
            payment = payments_db.get(payment_id)
            if not payment:
                bot.answer_callback_query(call.id, "❌ Платеж не найден.")
                return

            if payment['status'] != 'pending':
                bot.answer_callback_query(call.id, f"❌ Платеж уже {payment['status']}.")
                return

            user_id_p = payment['user_id']
            period = payment['period']
            amount, days = get_price_data(period)
            
            if action == 'confirm':
                payment['status'] = 'confirmed'
                add_subscription_time(user_id_p, days)
                save_data('payments.json', payments_db)
                
                send_config_to_user(user_id_p, user_id_p, period)
                
                bot.send_message(user_id_p, f"✅ Ваш платеж ({amount} ₽) подтвержден! Подписка на **{get_config_period_display(period)}** активирована.", parse_mode='Markdown')
                bot.edit_message_text(f"✅ Платеж #{payment_id} **подтвержден**.\nПользователю {user_id_p} выдана подписка.", call.message.chat.id, call.message.message_id)

            elif action == 'reject':
                payment['status'] = 'rejected'
                save_data('payments.json', payments_db)
                bot.send_message(user_id_p, f"❌ Ваш платеж ({amount} ₽) отклонен. Обратитесь в поддержку для уточнения.", parse_mode='Markdown')
                bot.edit_message_text(f"❌ Платеж #{payment_id} **отклонен**.", call.message.chat.id, call.message.message_id)
                
        bot.answer_callback_query(call.id)

def process_screenshot(message, payment_id):
    if not message.photo:
        msg = bot.send_message(message.chat.id, "❌ Пожалуйста, отправьте именно скриншот (фото). Попробуйте еще раз.")
        bot.register_next_step_handler(msg, process_screenshot, payment_id)
        return

    screenshot_id = message.photo[-1].file_id

    with DB_LOCK:
        payment = payments_db.get(payment_id)
        if not payment or payment['status'] != 'pending':
            bot.send_message(message.chat.id, "❌ Ошибка: платеж не в статусе ожидания.")
            return

        payment['screenshot_id'] = screenshot_id
        save_data('payments.json', payments_db)

    amount = payment['amount']
    user_id = payment['user_id']
    period = payment['period']
    
    confirm_keyboard = types.InlineKeyboardMarkup(row_width=2)
    confirm_keyboard.add(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_{payment_id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{payment_id}")
    )
    
    bot.send_photo(Config.ADMIN_ID, 
                   screenshot_id, 
                   caption=f"🔔 **Новая заявка на оплату!**\n\n"
                           f"Пользователь: `{user_id}`\n"
                           f"Период: **{get_config_period_display(period)}**\n"
                           f"Сумма: **{amount} ₽**\n",
                   parse_mode='Markdown', 
                   reply_markup=confirm_keyboard)
    
    bot.send_message(message.chat.id, "✅ Скриншот отправлен администратору. Ожидайте подтверждения.")

def process_add_config(message):
    if not is_admin(message.chat.id): return
    
    parts = message.text.split('\n')
    if len(parts) < 2:
        msg = bot.send_message(message.chat.id, "❌ Неверный формат. Введите период и хотя бы одну ссылку. Попробуйте снова.")
        bot.register_next_step_handler(msg, process_add_config)
        return

    period = parts[0].strip()
    config_urls = [url.strip() for url in parts[1:] if url.strip()]
    
    if period not in Config.PRICES:
        msg = bot.send_message(message.chat.id, f"❌ Неверный период. Допустимые: {', '.join(Config.PRICES.keys())}. Попробуйте снова.")
        bot.register_next_step_handler(msg, process_add_config)
        return

    added_count = 0
    duplicate_count = 0
    
    with DB_LOCK:
        if period not in configs_db:
            configs_db[period] = []

        existing_urls = set(configs_db[period])
        
        for url in config_urls:
            if url not in existing_urls:
                configs_db[period].append(url)
                existing_urls.add(url)
                added_count += 1
            else:
                duplicate_count += 1
        
        save_data('configs.json', configs_db)
    
    bot.send_message(message.chat.id, 
                     f"✅ **Результаты добавления конфигов:**\n"
                     f"Период: **{get_config_period_display(period)}**\n"
                     f"➕ Добавлено: {added_count} шт.\n"
                     f"🚫 Дубликатов: {duplicate_count} шт.", 
                     parse_mode='Markdown',
                     reply_markup=back_to_admin_keyboard())

def process_delete_config(message):
    if not is_admin(message.chat.id): return
    
    parts = message.text.strip().split(maxsplit=1)
    
    if len(parts) != 2:
        msg = bot.send_message(message.chat.id, "❌ Неверный формат. Введите `[период] [ссылка]`. Попробуйте снова.")
        bot.register_next_step_handler(msg, process_delete_config)
        return

    period, url_to_delete = parts
    
    if period not in Config.PRICES:
        msg = bot.send_message(message.chat.id, f"❌ Неверный период. Допустимые: {', '.join(Config.PRICES.keys())}. Попробуйте снова.")
        bot.register_next_step_handler(msg, process_delete_config)
        return

    with DB_LOCK:
        if period not in configs_db or url_to_delete not in configs_db[period]:
            bot.send_message(message.chat.id, f"❌ Конфиг `{url_to_delete}` не найден в списке на **{get_config_period_display(period)}**.", parse_mode='Markdown', reply_markup=back_to_admin_keyboard())
            return

        configs_db[period].remove(url_to_delete)
        save_data('configs.json', configs_db)
    
    bot.send_message(message.chat.id, f"✅ Конфиг `{url_to_delete}` на **{get_config_period_display(period)}** успешно удален.", parse_mode='Markdown', reply_markup=back_to_admin_keyboard())

@bot.message_handler(func=lambda message: message.text in ["📈 Статистика", "📢 Рассылка", "💰 Платежи", "👤 Управление пользователями"] and is_admin(message.chat.id))
def handle_admin_menu(message):
    chat_id = message.chat.id
    
    if message.text == "📈 Статистика":
        with DB_LOCK:
            total_users = len(users_db)
            active_subs = sum(1 for uid in users_db if get_subscription_days_left(uid) > 0)
            total_balance = sum(user.get('balance', 0) for user in users_db.values())
            pending_payments = sum(1 for p in payments_db.values() if p['status'] == 'pending')
        
        bot.send_message(chat_id, 
                         f"📈 **Общая статистика**\n\n"
                         f"👥 Всего пользователей: **{total_users}**\n"
                         f"🟢 Активных подписок: **{active_subs}**\n"
                         f"💰 Общий баланс пользователей: **{total_balance} ₽**\n"
                         f"⏳ Ожидающих платежей: **{pending_payments}**",
                         parse_mode='Markdown')

    elif message.text == "📢 Рассылка":
        msg = bot.send_message(chat_id, "📢 **Рассылка**\n\nВведите текст сообщения для рассылки всем пользователям.")
        bot.register_next_step_handler(msg, process_broadcast_text)

    elif message.text == "💰 Платежи":
        with DB_LOCK:
            pending_payments = [p for p in payments_db.values() if p['status'] == 'pending']
        
        if not pending_payments:
            bot.send_message(chat_id, "Нет ожидающих платежей.")
            return

        for p in pending_payments:
            payment_id = [k for k, v in payments_db.items() if v == p][0]
            user_id_p = p['user_id']
            period = p['period']
            amount = p['amount']
            screenshot_id = p['screenshot_id']

            confirm_keyboard = types.InlineKeyboardMarkup(row_width=2)
            confirm_keyboard.add(
                types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_{payment_id}"),
                types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{payment_id}")
            )
            
            caption = (f"🔔 **Ожидающий платеж #{payment_id}**\n\n"
                       f"Пользователь: `{user_id_p}`\n"
                       f"Период: **{get_config_period_display(period)}**\n"
                       f"Сумма: **{amount} ₽**\n"
                       f"Скриншот: {'✅ Есть' if screenshot_id else '❌ Нет'}")
            
            if screenshot_id:
                bot.send_photo(chat_id, screenshot_id, caption=caption, parse_mode='Markdown', reply_markup=confirm_keyboard)
            else:
                bot.send_message(chat_id, caption, parse_mode='Markdown', reply_markup=confirm_keyboard)

    elif message.text == "👤 Управление пользователями":
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔎 Найти/Изменить пользователя", callback_data="admin_find_user"))
        keyboard.add(types.InlineKeyboardButton("🚫 Заблокировать/Разблокировать", callback_data="admin_ban_user"))
        bot.send_message(chat_id, "👤 **Управление пользователями**", reply_markup=keyboard, parse_mode='Markdown')

def process_broadcast_text(message):
    if not is_admin(message.chat.id): return
    
    broadcast_text = message.text
    sent_count = 0
    failed_count = 0
    
    bot.send_message(message.chat.id, "📢 Начинаю рассылку...")
    
    for uid in list(users_db.keys()):
        try:
            bot.send_message(uid, f"📢 **Объявление от администратора:**\n\n{broadcast_text}", parse_mode='Markdown')
            sent_count += 1
            time.sleep(Config.BROADCAST_DELAY_SEC)
        except Exception as e:
            failed_count += 1
            
    bot.send_message(message.chat.id, 
                    f"✅ Рассылка завершена!\n"
                    f"📤 Отправлено: {sent_count}\n"
                    f"❌ Не отправлено: {failed_count}",
                    reply_markup=admin_keyboard())

@bot.message_handler(commands=['manage'])
def handle_manage_command(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "У вас нет прав администратора.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "❌ Неверный формат. Используйте `/manage [ID_пользователя]`.")
        return
        
    try:
        user_id_target = parts[1]
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "❌ Неверный формат ID пользователя.")
        return

    display_user_info(message.chat.id, user_id_target)

def display_user_info(admin_chat_id, target_id):
    with DB_LOCK:
        user_data = users_db.get(target_id)

    if not user_data:
        bot.send_message(admin_chat_id, f"❌ Пользователь с ID `{target_id}` не найден.", parse_mode='Markdown')
        return

    days_left = get_subscription_days_left(target_id)
    sub_end = user_data.get('subscription_end') or 'Нет'
    
    info_text = (f"👤 **Пользователь ID: {target_id}**\n\n"
                 f"Имя: **{user_data.get('first_name', 'N/A')}**\n"
                 f"Username: **@{user_data.get('username', 'N/A')}**\n"
                 f"Баланс: **{user_data.get('balance', 0)} ₽**\n"
                 f"Подписка до: **{sub_end}** ({days_left} дней)\n"
                 f"Конфиг: **{'✅ Есть' if user_data.get('config_url') else '❌ Нет'}**\n"
                 f"Заблокирован: **{'Да' if user_data.get('is_banned') else 'Нет'}**")

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("✏️ Изменить баланс", callback_data=f"admin_edit_balance_{target_id}"))
    markup.add(types.InlineKeyboardButton("⏳ Изменить подписку", callback_data=f"admin_edit_sub_{target_id}"))
    markup.add(types.InlineKeyboardButton(f"{'🔓 Разблокировать' if user_data.get('is_banned') else '🚫 Заблокировать'}", callback_data=f"admin_toggle_ban_{target_id}"))

    bot.send_message(admin_chat_id, info_text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_edit_balance_') or call.data.startswith('admin_edit_sub_') or call.data.startswith('admin_toggle_ban_'))
def handle_admin_edit_callbacks(call):
    if not is_admin(call.message.chat.id): return
    
    parts = call.data.split('_')
    action = parts[2]
    target_id = parts[3]
    
    if action == 'balance':
        msg = bot.send_message(call.message.chat.id, f"Введите новый баланс для пользователя **{target_id}** (целое число):", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_edit_balance, target_id)
    
    elif action == 'sub':
        msg = bot.send_message(call.message.chat.id, f"Введите количество дней для **добавления** к подписке пользователя **{target_id}** (целое число):", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_edit_subscription, target_id)

    elif action == 'ban':
        with DB_LOCK:
            user_data = users_db.get(target_id)
            if not user_data:
                bot.answer_callback_query(call.id, "Пользователь не найден.")
                return
            
            is_banned = user_data.get('is_banned', False)
            user_data['is_banned'] = not is_banned
            save_data('users.json', users_db)
            
            status_text = "заблокирован" if not is_banned else "разблокирован"
            bot.answer_callback_query(call.id, f"Пользователь {target_id} {status_text}.")
            bot.send_message(call.message.chat.id, f"Пользователь **{target_id}** успешно **{status_text}**.", parse_mode='Markdown')
            display_user_info(call.message.chat.id, target_id)
            bot.send_message(target_id, f"🔔 Ваш аккаунт был **{status_text}** администратором.", parse_mode='Markdown')

def process_edit_balance(message, target_id):
    if not is_admin(message.chat.id): return
    
    try:
        new_balance = int(message.text.strip())
        if new_balance < 0:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Неверный формат баланса. Должно быть положительное целое число. Попробуйте снова.")
        bot.register_next_step_handler(msg, process_edit_balance, target_id)
        return

    with DB_LOCK:
        if target_id not in users_db:
            bot.send_message(message.chat.id, f"❌ Пользователь {target_id} не найден.")
            return

        users_db[target_id]['balance'] = new_balance
        save_data('users.json', users_db)
    
    bot.send_message(message.chat.id, f"✅ Баланс пользователя **{target_id}** изменен на **{new_balance} ₽**.", parse_mode='Markdown')
    display_user_info(message.chat.id, target_id)
    bot.send_message(target_id, f"🔔 Ваш баланс был изменен администратором и теперь составляет **{new_balance} ₽**.", parse_mode='Markdown')

def process_edit_subscription(message, target_id):
    if not is_admin(message.chat.id): return
    
    try:
        add_days = int(message.text.strip())
        if add_days < 1:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Неверное количество дней. Должно быть положительное целое число. Попробуйте снова.")
        bot.register_next_step_handler(msg, process_edit_subscription, target_id)
        return

    add_subscription_time(target_id, add_days)
    
    bot.send_message(message.chat.id, f"✅ Подписка пользователя **{target_id}** продлена на **{add_days}** дней.", parse_mode='Markdown')
    display_user_info(message.chat.id, target_id)
    bot.send_message(target_id, f"🔔 Ваша подписка была продлена администратором на **{add_days}** дней.", parse_mode='Markdown')

def signal_handler(signum, frame):
    print(f"Получен сигнал {signum}. Корректно останавливаю бота...")
    bot.stop_polling()
    print("Бот остановлен.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    print("Бот запускается...")
    try:
        if Config.ADMIN_ID == 8320218178:
            print("Внимание: ADMIN_ID не изменен. Пожалуйста, замените его на ваш фактический ID в файле.")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Критическая ошибка при запуске бота: {e}")
