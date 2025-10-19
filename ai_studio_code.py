import telebot
from telebot import types
import json
import time
import datetime
import threading

# --- КОНСТАНТЫ ---
TOKEN = '8217097426:AAEXU3BJ55Bkx-cfOEtRTxkPaOYC1zvRfO8'
ADMIN_USERNAME = '@Gl1ch555'
ADMIN_ID = 8320218178 # Ваш ID, который вы предоставили
CARD_NUMBER = '2204320690808227'
CARD_HOLDER = 'Makarov Pavel Alexandrovich (Ozon Bank)'

PRICE_MONTH = 50
PRICE_2_MONTHS = 90 # Со скидкой
PRICE_3_MONTHS = 120 # Со скидкой

REFERRAL_BONUS_RUB = 25
REFERRAL_BONUS_DAYS = 7 # Дней подписки за реферала

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = telebot.TeleBot(TOKEN)

# --- БАЗЫ ДАННЫХ (ПРОСТОЙ JSON) ---
# Для реального проекта рекомендуется использовать СУБД (PostgreSQL, SQLite)
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
# users_db: { user_id: { 'balance': 0, 'subscription_end': None, 'referred_by': None, 'username': '...', 'first_name': '...', 'referrals_count': 0 } }
# configs_db: { '1_month': [ { 'name': 'Germany 1', 'image': 'url_to_image', 'code': 'config_code', 'link': 'link_to_config' }, ... ], '2_months': [], '3_months': [] }
# payments_db: { payment_id: { 'user_id': ..., 'amount': ..., 'status': 'pending/confirmed/rejected', 'screenshot_id': ..., 'timestamp': ..., 'period': ... } }

# --- ГЕНЕРАТОР УНИКАЛЬНОГО ID ДЛЯ ПЛАТЕЖЕЙ ---
def generate_payment_id():
    return str(int(time.time() * 100000))

# --- ФУНКЦИИ АДМИНКИ ---
def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Управление конфигами", callback_data="admin_manage_configs"),
        types.InlineKeyboardButton("Подтвердить платежи", callback_data="admin_confirm_payments"),
        types.InlineKeyboardButton("Список пользователей", callback_data="admin_users_list"),
        types.InlineKeyboardButton("Изменить баланс/подписку", callback_data="admin_edit_user"),
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
        types.InlineKeyboardButton("Назад в админку", callback_data="admin_panel")
    )
    return markup

def confirm_payments_keyboard(payment_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Подтвердить", callback_data=f"admin_confirm_{payment_id}"),
        types.InlineKeyboardButton("Отклонить", callback_data=f"admin_reject_{payment_id}")
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

def payment_methods_keyboard(period_callback_data, amount):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"Оплата картой ({amount} ₽)", callback_data=f"pay_card_{period_callback_data}"),
        types.InlineKeyboardButton(f"Оплата Telegram Stars ({amount} Stars)", callback_data=f"pay_stars_{period_callback_data}"),
        types.InlineKeyboardButton("Назад", callback_data="buy_vpn")
    )
    return markup

def my_account_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Запросить конфиг", callback_data="request_config"),
        types.InlineKeyboardButton("Продлить подписку", callback_data="buy_vpn"),
        types.InlineKeyboardButton("Назад", callback_data="main_menu")
    )
    return markup

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
                    users_db[potential_referrer_id]['referrals_count'] = users_db[potential_referrer_id].get('referrals_count', 0) + 1
                    users_db[potential_referrer_id]['balance'] = users_db[potential_referrer_id].get('balance', 0) + REFERRAL_BONUS_RUB
                    
                    # Добавляем дни подписки рефереру, если у него есть активная подписка
                    if users_db[potential_referrer_id].get('subscription_end'):
                        current_end = datetime.datetime.strptime(users_db[potential_referrer_id]['subscription_end'], '%Y-%m-%d %H:%M:%S')
                        new_end = current_end + datetime.timedelta(days=REFERRAL_BONUS_DAYS)
                        users_db[potential_referrer_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
                        bot.send_message(potential_referrer_id, 
                                         f"🎉 Ваш реферал @{username} зарегистрировался по вашей ссылке! "
                                         f"Вам начислено {REFERRAL_BONUS_RUB} ₽ на баланс и {REFERRAL_BONUS_DAYS} дней к подписке!")
                    else:
                        bot.send_message(potential_referrer_id, 
                                         f"🎉 Ваш реферал @{username} зарегистрировался по вашей ссылке! "
                                         f"Вам начислено {REFERRAL_BONUS_RUB} ₽ на баланс.")

                    save_data('users.json', users_db)
            except ValueError:
                pass # Если реферальный ID некорректен

        users_db[user_id] = {
            'balance': 0,
            'subscription_end': None,
            'referred_by': referred_by_id,
            'username': username,
            'first_name': first_name,
            'referrals_count': 0
        }
        save_data('users.json', users_db)

    bot.send_message(message.chat.id, "Привет! Добро пожаловать в VPN Bot!",
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
        
        bot.edit_message_text(f"Вы выбрали подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}. "
                              f"К оплате: {amount} ₽.\nВыберите способ оплаты:",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=payment_methods_keyboard(period_data, amount))

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
                         reply_markup=main_menu_keyboard(ADMIN_ID)) # Админка всегда доступна из главного меню

    elif call.data.startswith("pay_stars_"):
        period_data = call.data.replace("pay_stars_", "")
        amount = 0
        if period_data == "1_month":
            amount = PRICE_MONTH
        elif period_data == "2_months":
            amount = PRICE_2_MONTHS
        elif period_data == "3_months":
            amount = PRICE_3_MONTHS
        
        # Для оплаты Stars нужна специальная логика Telegram Payments.
        # Это упрощенная заглушка. Для реальной работы нужно использовать invoices.
        bot.edit_message_text(f"Оплата Telegram Stars пока находится в разработке! "
                              f"Пожалуйста, используйте оплату картой.\n\n"
                              f"К оплате: {amount} Stars.",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=buy_vpn_keyboard())

    # --- ЛИЧНЫЙ КАБИНЕТ ---
    elif call.data == "my_account":
        user_info = users_db.get(user_id, {})
        subscription_end = user_info.get('subscription_end')
        balance = user_info.get('balance', 0)

        status_text = "Нет активной подписки"
        if subscription_end:
            end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
            if end_date > datetime.datetime.now():
                status_text = f"Подписка активна до: {end_date.strftime('%d.%m.%Y %H:%M')}"
            else:
                status_text = "Подписка истекла"
                users_db[user_id]['subscription_end'] = None # Обнуляем, если истекла
                save_data('users.json', users_db)

        bot.edit_message_text(f"👤 Ваш личный кабинет:\n\n"
                              f"Статус подписки: {status_text}\n"
                              f"Баланс: {balance} ₽\n"
                              f"Ваше имя: {user_info.get('first_name', 'N/A')}\n"
                              f"Ваш username: @{user_info.get('username', 'N/A')}\n\n",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=my_account_keyboard())

    elif call.data == "request_config":
        user_info = users_db.get(user_id, {})
        subscription_end = user_info.get('subscription_end')

        if subscription_end:
            end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
            if end_date > datetime.datetime.now():
                # Проверяем, есть ли конфиги
                available_configs = []
                for period, configs_list in configs_db.items():
                    available_configs.extend(configs_list)

                if available_configs:
                    # Просто выдаем первый попавшийся конфиг, для простоты
                    # В реальной системе можно выдавать уникальный или по запросу
                    config = available_configs[0]
                    bot.send_message(call.message.chat.id, "Вот ваш VPN конфиг:")
                    if config.get('image'):
                        bot.send_photo(call.message.chat.id, config['image'])
                    bot.send_message(call.message.chat.id, 
                                     f"**Имя:** {config['name']}\n"
                                     f"**Код:** `{config['code']}`\n"
                                     f"**Ссылка:** {config['link']}",
                                     parse_mode='Markdown')
                else:
                    bot.send_message(call.message.chat.id, "К сожалению, сейчас нет доступных VPN-конфигов. Обратитесь в поддержку.")
            else:
                bot.send_message(call.message.chat.id, "Ваша подписка истекла. Пожалуйста, продлите ее.")
        else:
            bot.send_message(call.message.chat.id, "У вас нет активной подписки. Приобретите ее, чтобы получить конфиг.")
        
        bot.send_message(call.message.chat.id, "Что еще вы хотите сделать?", reply_markup=main_menu_keyboard(user_id))

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
                              f"Приглашайте друзей и получайте бонусы!\n"
                              f"За каждого приглашенного пользователя, который зарегистрируется по вашей ссылке, "
                              f"вы получите {REFERRAL_BONUS_RUB} ₽ на баланс и {REFERRAL_BONUS_DAYS} дней к активной подписке.\n\n"
                              f"Ваша реферальная ссылка: `{referral_link}`\n\n"
                              f"Количество ваших рефералов: {referrals_count}\n"
                              f"Ваш реферальный баланс: {balance} ₽",
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
                        message_text += f"  {i+1}. Имя: {config['name']}, Код: `{config['code']}` (ID: {i})\n"
                else:
                    message_text += "  (Нет конфигов)\n"
            
            bot.edit_message_text(message_text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown', reply_markup=manage_configs_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_add_config":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите данные конфига в формате:\n"
                                                  "`период_подписки|название_конфига|url_изображения|код_конфига|ссылка_на_конфиг`\n"
                                                  "Пример: `1_month|Germany 1|https://example.com/image.png|config_code_here|https://example.com/config.ovpn`\n"
                                                  "Поддерживаемые периоды: `1_month`, `2_months`, `3_months`\n"
                                                  "Если изображения нет, можно использовать `none` вместо url.")
            bot.register_next_step_handler(call.message, process_add_config)
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
                    bot.send_photo(ADMIN_ID, p_data['screenshot_id'], 
                                   caption=f"Платеж ID: {payment_id}\n"
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

                    bot.send_message(target_user_id, 
                                     f"✅ Ваш платеж за подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')} подтвержден!\n"
                                     f"Ваша подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                     f"Можете запросить конфиг в личном кабинете.",
                                     reply_markup=main_menu_keyboard(target_user_id))
                
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

    elif call.data == "admin_users_list":
        if str(user_id) == str(ADMIN_ID):
            message_text = "**Список пользователей:**\n\n"
            for uid, u_data in users_db.items():
                sub_end_str = "Нет"
                if u_data.get('subscription_end'):
                    sub_end = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                    if sub_end > datetime.datetime.now():
                        sub_end_str = sub_end.strftime('%d.%m.%Y %H:%M')
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
    
    elif call.data == "admin_edit_user":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите ID пользователя, которого хотите изменить.")
            bot.register_next_step_handler(call.message, process_edit_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_broadcast":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(call.message.chat.id, "Введите сообщение для рассылки всем пользователям.")
            bot.register_next_step_handler(call.message, process_broadcast_message)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

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
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                       caption=f"❗️ Новый скриншот платежа ID: {pending_payment}\n"
                               f"От: @{message.from_user.username} (ID: {user_id})\n"
                               f"Сумма: {payments_db[pending_payment]['amount']} ₽\n"
                               f"Период: {payments_db[pending_payment]['period'].replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}\n"
                               f"Время: {payments_db[pending_payment]['timestamp']}",
                       reply_markup=confirm_payments_keyboard(pending_payment))
    else:
        bot.send_message(message.chat.id, "Не могу найти ожидающий платеж для этого скриншота. "
                                         "Возможно, вы уже отправили скриншот или не инициировали платеж. "
                                         "Если возникли проблемы, обратитесь в поддержку (@Gl1ch555).")

# --- СЛЕДУЮЩИЕ ШАГИ ДЛЯ АДМИНКИ ---
def process_add_config(message):
    user_id = str(message.from_user.id)
    if user_id != str(ADMIN_ID): return

    try:
        parts = message.text.split('|')
        if len(parts) != 5:
            raise ValueError("Некорректный формат. Используйте `период|название|url_изображения|код|ссылка`")
        
        period, name, image_url, code, link = [p.strip() for p in parts]
        if period not in ['1_month', '2_months', '3_months']:
            raise ValueError("Некорректный период подписки.")
        
        new_config = {
            'name': name,
            'image': image_url if image_url.lower() != 'none' else None,
            'code': code,
            'link': link
        }
        
        if period not in configs_db:
            configs_db[period] = []
        configs_db[period].append(new_config)
        save_data('configs.json', configs_db)
        
        bot.send_message(user_id, "Конфиг успешно добавлен!", reply_markup=admin_keyboard())
    except Exception as e:
        bot.send_message(user_id, f"Ошибка при добавлении конфига: {e}\nПопробуйте еще раз.", reply_markup=admin_keyboard())

def process_delete_config(message):
    user_id = str(message.from_user.id)
    if user_id != str(ADMIN_ID): return

    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError("Некорректный формат. Используйте `период_подписки ID`")
        
        period, config_id_str = parts
        config_id = int(config_id_str)

        if period not in configs_db:
            raise ValueError(f"Период '{period}' не найден.")
        
        if not (0 <= config_id < len(configs_db[period])):
            raise ValueError("Некорректный ID конфига для этого периода.")
        
        deleted_config = configs_db[period].pop(config_id)
        save_data('configs.json', configs_db)
        
        bot.send_message(user_id, f"Конфиг '{deleted_config['name']}' ({period}) успешно удален.", reply_markup=admin_keyboard())
    except Exception as e:
        bot.send_message(user_id, f"Ошибка при удалении конфига: {e}\nПопробуйте еще раз.", reply_markup=admin_keyboard())

def process_edit_user_id(message):
    user_id = str(message.from_user.id)
    if user_id != str(ADMIN_ID): return

    target_user_id = message.text.strip()
    if target_user_id not in users_db:
        bot.send_message(user_id, "Пользователь с таким ID не найден.", reply_markup=admin_keyboard())
        return

    bot.send_message(user_id, f"Пользователь {target_user_id} (@{users_db[target_user_id].get('username', 'N/A')}).\n"
                               "Введите, что хотите изменить:\n"
                               "`balance <новое_значение>` (например, `balance 100`)\n"
                               "`sub_end <ГГГГ-ММ-ДД ЧЧ:ММ:СС>` (например, `sub_end 2024-12-31 23:59:59` или `sub_end none` для сброса)\n"
                               "Или `cancel` для отмены.")
    bot.register_next_step_handler(message, process_edit_user_data, target_user_id)

def process_edit_user_data(message, target_user_id):
    user_id = str(message.from_user.id)
    if user_id != str(ADMIN_ID): return

    command = message.text.strip().lower()

    if command == 'cancel':
        bot.send_message(user_id, "Изменение пользователя отменено.", reply_markup=admin_keyboard())
        return

    try:
        parts = command.split(' ', 1)
        action = parts[0]
        value = parts[1] if len(parts) > 1 else None

        if action == 'balance' and value:
            new_balance = int(value)
            users_db[target_user_id]['balance'] = new_balance
            bot.send_message(user_id, f"Баланс пользователя {target_user_id} изменен на {new_balance} ₽.", reply_markup=admin_keyboard())
            bot.send_message(target_user_id, f"Администратор изменил ваш баланс. Текущий баланс: {new_balance} ₽.")
        elif action == 'sub_end' and value:
            if value.lower() == 'none':
                users_db[target_user_id]['subscription_end'] = None
                bot.send_message(user_id, f"Подписка пользователя {target_user_id} сброшена.", reply_markup=admin_keyboard())
                bot.send_message(target_user_id, "Администратор сбросил вашу подписку.")
            else:
                new_sub_end = datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                users_db[target_user_id]['subscription_end'] = new_sub_end.strftime('%Y-%m-%d %H:%M:%S')
                bot.send_message(user_id, f"Подписка пользователя {target_user_id} установлена до {new_sub_end.strftime('%d.%m.%Y %H:%M')}.", reply_markup=admin_keyboard())
                bot.send_message(target_user_id, f"Администратор изменил срок вашей подписки. Новая дата окончания: {new_sub_end.strftime('%d.%m.%Y %H:%M')}.")
        else:
            raise ValueError("Неизвестное действие или отсутствующее значение.")
        
        save_data('users.json', users_db)

    except ValueError as ve:
        bot.send_message(user_id, f"Ошибка формата: {ve}\nПопробуйте еще раз или `cancel`.", reply_markup=admin_keyboard())
        bot.register_next_step_handler(message, process_edit_user_data, target_user_id)
    except Exception as e:
        bot.send_message(user_id, f"Произошла непредвиденная ошибка: {e}\nПопробуйте еще раз или `cancel`.", reply_markup=admin_keyboard())
        bot.register_next_step_handler(message, process_edit_user_data, target_user_id)

def process_broadcast_message(message):
    user_id = str(message.from_user.id)
    if user_id != str(ADMIN_ID): return

    broadcast_text = message.text
    sent_count = 0
    failed_count = 0

    bot.send_message(user_id, "Начинаю рассылку...")

    for uid in users_db.keys():
        try:
            bot.send_message(uid, f"**Объявление от администратора:**\n\n{broadcast_text}", parse_mode='Markdown')
            sent_count += 1
            time.sleep(0.1) # Задержка, чтобы не превысить лимиты API Telegram
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {uid}: {e}")
            failed_count += 1
    
    bot.send_message(user_id, f"Рассылка завершена. Отправлено {sent_count} сообщений, не отправлено {failed_count}.", reply_markup=admin_keyboard())

# --- ЗАПУСК БОТА ---
print("Бот запущен...")
bot.polling(none_stop=True)
