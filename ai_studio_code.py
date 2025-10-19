import telebot
from telebot import types
import json
import time
import datetime
import threading
import hashlib # Для генерации стабильного ID для Stars платежей

# --- КОНСТАНТЫ ---
TOKEN = '8217097426:AAEXU3BJ55Bkx-cfOEtRTxkPaOYC1zvRfO8'
ADMIN_USERNAME = '@Gl1ch555'
ADMIN_ID = 8320218178 # Ваш ID, который вы предоставили
CARD_NUMBER = '2204320690808227'
CARD_HOLDER = 'Makarov Pavel Alexandrovich (Ozon Bank)'

PRICE_MONTH = 50
PRICE_2_MONTHS = 90 # Со скидкой
PRICE_3_MONTHS = 120 # Со скидкой

STARS_PRICE_MONTH = 50 # 1 Star = 1 Ruble для простоты
STARS_PRICE_2_MONTHS = 90
STARS_PRICE_3_MONTHS = 120

REFERRAL_BONUS_RUB = 25
REFERRAL_BONUS_DAYS = 7 # Дней подписки за реферала

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = telebot.TeleBot(TOKEN)

# --- БАЗЫ ДАННЫХ (ПРОСТОЙ JSON) ---
def load_data(filename, default_value={}):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_value

def save_data(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

users_db = load_data('users.json')
configs_db = load_data('configs.json', default_value={'1_month': [], '2_months': [], '3_months': []})
payments_db = load_data('payments.json')

# --- МОДЕЛИ ДАННЫХ ---
# users_db: { user_id: { 'balance': 0, 'subscription_end': None, 'referred_by': None, 'username': '...', 'first_name': '...', 'referrals_count': 0 } }
# configs_db: { '1_month': [ { 'name': 'Germany 1', 'link': 'vless://...', 'is_used': False }, ... ], ... }
# payments_db: { payment_id: { 'user_id': ..., 'amount': ..., 'status': 'pending/confirmed/rejected', 'screenshot_id': ..., 'timestamp': ..., 'period': ..., 'method': 'card/stars' } }

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
        types.InlineKeyboardButton("Добавить конфиги", callback_data="admin_add_config"),
        types.InlineKeyboardButton("Удалить конфиг (в разработке)", callback_data="admin_delete_config_disabled"),
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

def choose_config_period_for_add_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("1 месяц", callback_data="admin_add_config_1_month"),
        types.InlineKeyboardButton("2 месяца", callback_data="admin_add_config_2_months"),
        types.InlineKeyboardButton("3 месяца", callback_data="admin_add_config_3_months"),
        types.InlineKeyboardButton("Отмена", callback_data="admin_panel")
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
        types.InlineKeyboardButton(f"1 месяц ({PRICE_MONTH} ₽ / {STARS_PRICE_MONTH} ⭐)", callback_data="choose_period_1_month"),
        types.InlineKeyboardButton(f"2 месяца ({PRICE_2_MONTHS} ₽ / {STARS_PRICE_2_MONTHS} ⭐)", callback_data="choose_period_2_months"),
        types.InlineKeyboardButton(f"3 месяца ({PRICE_3_MONTHS} ₽ / {STARS_PRICE_3_MONTHS} ⭐)", callback_data="choose_period_3_months"),
        types.InlineKeyboardButton("Назад", callback_data="main_menu")
    )
    return markup

def payment_methods_keyboard(period_callback_data, amount_rub, amount_stars):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"Оплата картой ({amount_rub} ₽)", callback_data=f"pay_card_{period_callback_data}"),
        types.InlineKeyboardButton(f"Оплата Telegram Stars ({amount_stars} ⭐)", callback_data=f"pay_stars_{period_callback_data}"),
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
                pass 

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
    current_chat_id = call.message.chat.id
    current_message_id = call.message.message_id

    if call.data == "main_menu":
        bot.edit_message_text("Главное меню:", chat_id=current_chat_id, message_id=current_message_id,
                              reply_markup=main_menu_keyboard(user_id))
    
    # --- ПОКУПКА VPN ---
    elif call.data == "buy_vpn":
        bot.edit_message_text("Выберите срок подписки:", chat_id=current_chat_id, message_id=current_message_id,
                              reply_markup=buy_vpn_keyboard())
    
    elif call.data.startswith("choose_period_"):
        period_data = call.data.replace("choose_period_", "") 
        amount_rub = 0
        amount_stars = 0
        if period_data == "1_month":
            amount_rub = PRICE_MONTH
            amount_stars = STARS_PRICE_MONTH
        elif period_data == "2_months":
            amount_rub = PRICE_2_MONTHS
            amount_stars = STARS_PRICE_2_MONTHS
        elif period_data == "3_months":
            amount_rub = PRICE_3_MONTHS
            amount_stars = STARS_PRICE_3_MONTHS
        
        bot.edit_message_text(f"Вы выбрали подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}. "
                              f"К оплате: {amount_rub} ₽ или {amount_stars} ⭐.\nВыберите способ оплаты:",
                              chat_id=current_chat_id, message_id=current_message_id,
                              reply_markup=payment_methods_keyboard(period_data, amount_rub, amount_stars))

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
                              chat_id=current_chat_id, message_id=current_message_id,
                              parse_mode='Markdown')
        
        # Уведомляем админа о новом платеже
        bot.send_message(ADMIN_ID, 
                         f"🔔 Новый платеж на {amount} ₽ от @{call.from_user.username} (ID: {user_id}) за {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}. "
                         f"Ожидает скриншот.", 
                         reply_markup=main_menu_keyboard(ADMIN_ID)) 

    elif call.data.startswith("pay_stars_"):
        period_data = call.data.replace("pay_stars_", "")
        amount_stars = 0
        title = ""
        description = ""

        if period_data == "1_month":
            amount_stars = STARS_PRICE_MONTH
            title = "Подписка VPN на 1 месяц"
            description = "Получите доступ к быстрому и безопасному VPN на 30 дней."
        elif period_data == "2_months":
            amount_stars = STARS_PRICE_2_MONTHS
            title = "Подписка VPN на 2 месяца"
            description = "Получите доступ к быстрому и безопасному VPN на 60 дней."
        elif period_data == "3_months":
            amount_stars = STARS_PRICE_3_MONTHS
            title = "Подписка VPN на 3 месяца"
            description = "Получите доступ к быстрому и безопасному VPN на 90 дней."
        
        # Создаем уникальный инвойс-payload для каждого платежа
        invoice_payload = f"{user_id}_{period_data}_{generate_payment_id()}"
        
        # Записываем платеж в базу как pending (до того, как пользователь оплатит)
        payments_db[invoice_payload] = { # Используем invoice_payload как payment_id для Stars
            'user_id': user_id,
            'amount': amount_stars, # Здесь amount - это Stars
            'status': 'pending',
            'screenshot_id': None, # Для Stars скриншот не нужен
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'period': period_data,
            'method': 'stars'
        }
        save_data('payments.json', payments_db)

        bot.send_invoice(
            chat_id=current_chat_id,
            title=title,
            description=description,
            invoice_payload=invoice_payload,
            provider_token='', # Для Telegram Stars provider_token не нужен
            currency='XTR', # Валюта для Telegram Stars
            prices=[types.LabeledPrice(label=title, amount=amount_stars * 100)], # Сумма в копейках/центах (Stars - целые числа)
            max_tip_amount=0, # Не разрешаем чаевые
            suggested_tip_amounts=[],
            start_parameter='vpn_stars_payment',
            reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Оплатить ⭐", pay=True))
        )
        bot.answer_callback_query(call.id) # Закрываем callback

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
                users_db[user_id]['subscription_end'] = None 
                save_data('users.json', users_db)

        bot.edit_message_text(f"👤 Ваш личный кабинет:\n\n"
                              f"Статус подписки: {status_text}\n"
                              f"Баланс: {balance} ₽\n"
                              f"Ваше имя: {user_info.get('first_name', 'N/A')}\n"
                              f"Ваш username: @{user_info.get('username', 'N/A')}\n\n",
                              chat_id=current_chat_id, message_id=current_message_id,
                              reply_markup=my_account_keyboard())

    elif call.data == "request_config":
        user_info = users_db.get(user_id, {})
        subscription_end = user_info.get('subscription_end')

        if subscription_end:
            end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
            if end_date > datetime.datetime.now():
                # Ищем неиспользованный конфиг
                found_config = None
                for period_key in ['1_month', '2_months', '3_months']: # Можно добавить логику выбора по периоду подписки
                    for i, config in enumerate(configs_db.get(period_key, [])):
                        if not config.get('is_used', False):
                            found_config = config
                            configs_db[period_key][i]['is_used'] = True # Помечаем как использованный
                            save_data('configs.json', configs_db)
                            break
                    if found_config:
                        break

                if found_config:
                    bot.send_message(current_chat_id, "Вот ваш VPN конфиг:")
                    # Имя генерируется из имени пользователя, как вы просили, но в конфиге его нет, поэтому берем из пользователя
                    config_name = f"VPN для @{user_info.get('username', user_id)}" 
                    bot.send_message(current_chat_id, 
                                     f"**Имя:** {config_name}\n"
                                     f"**Ссылка на подписку (VLESS):** `{found_config['link']}`\n\n"
                                     f"Для использования скопируйте ссылку и добавьте её в приложение V2RayNG/Nekobox/Shadowrocket и т.п.",
                                     parse_mode='Markdown')
                else:
                    bot.send_message(current_chat_id, "К сожалению, сейчас нет доступных VPN-конфигов. Обратитесь в поддержку.",
                                     reply_markup=my_account_keyboard())
            else:
                bot.send_message(current_chat_id, "Ваша подписка истекла. Пожалуйста, продлите ее.",
                                 reply_markup=my_account_keyboard())
        else:
            bot.send_message(current_chat_id, "У вас нет активной подписки. Приобретите ее, чтобы получить конфиг.",
                             reply_markup=my_account_keyboard())
        
        bot.send_message(current_chat_id, "Что еще вы хотите сделать?", reply_markup=main_menu_keyboard(user_id))

    # --- ПОДДЕРЖКА ---
    elif call.data == "support":
        bot.edit_message_text(f"Для связи с поддержкой напишите @Gl1ch555.\n"
                              f"Постараемся ответить как можно скорее.",
                              chat_id=current_chat_id, message_id=current_message_id,
                              reply_markup=main_menu_keyboard(user_id))

    # --- РЕФЕРАЛЬНАЯ СИСТЕМА ---
    elif call.data == "referral_system":
        referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        user_info = users_db.get(user_id, {})
        referrals_count = user_info.get('referrals_count', 0)
        balance = user_info.get('balance', 0)

        referral_explanation = (
            "**Как работает реферальная система?**\n"
            "Пригласите друга по вашей уникальной ссылке. "
            "Когда он запустит бота по вашей ссылке и зарегистрируется, "
            "вы автоматически получите **{RUB} ₽** на баланс и **{DAYS} дней** к вашей активной подписке.\n"
            "Чем больше друзей вы пригласите, тем больше бонусов получите!\n\n"
        ).format(RUB=REFERRAL_BONUS_RUB, DAYS=REFERRAL_BONUS_DAYS)

        bot.edit_message_text(f"🤝 **Реферальная система**\n\n"
                              f"{referral_explanation}"
                              f"Ваша реферальная ссылка: `{referral_link}`\n\n"
                              f"Количество ваших рефералов: {referrals_count}\n"
                              f"Ваш реферальный баланс: {balance} ₽",
                              chat_id=current_chat_id, message_id=current_message_id,
                              parse_mode='Markdown', reply_markup=main_menu_keyboard(user_id))

    # --- АДМИН-ПАНЕЛЬ ---
    elif call.data == "admin_panel":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("🛠️ Админ-панель:", chat_id=current_chat_id, message_id=current_message_id,
                                  reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
            bot.edit_message_text("Главное меню:", chat_id=current_chat_id, message_id=current_message_id,
                                  reply_markup=main_menu_keyboard(user_id))

    elif call.data == "admin_manage_configs":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Управление конфигами:", chat_id=current_chat_id, message_id=current_message_id,
                                  reply_markup=manage_configs_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_show_configs":
        if str(user_id) == str(ADMIN_ID):
            message_text = "**Текущие конфиги (свободные/использованные):**\n\n"
            for period, configs_list in configs_db.items():
                message_text += f"**{period.replace('_', ' ').capitalize()}:**\n"
                if configs_list:
                    for i, config in enumerate(configs_list):
                        status = "✅ Свободен" if not config.get('is_used', False) else "❌ Использован"
                        message_text += f"  {i+1}. {status} - `{config['link']}`\n"
                else:
                    message_text += "  (Нет конфигов)\n"
            
            bot.edit_message_text(message_text, chat_id=current_chat_id, message_id=current_message_id,
                                  parse_mode='Markdown', reply_markup=manage_configs_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_add_config":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Выберите срок, на который добавляете конфиги:", chat_id=current_chat_id, message_id=current_message_id,
                                  reply_markup=choose_config_period_for_add_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data.startswith("admin_add_config_"):
        if str(user_id) == str(ADMIN_ID):
            period_to_add = call.data.replace("admin_add_config_", "")
            bot.edit_message_text(f"Отлично! Теперь отправьте **список ссылок на VLESS конфиги** (по одной ссылке на строку, через Enter) "
                                  f"для подписки на **{period_to_add.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}**.",
                                  chat_id=current_chat_id, message_id=current_message_id)
            bot.register_next_step_handler(call.message, process_bulk_add_configs, period_to_add)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_delete_config_disabled":
        bot.answer_callback_query(call.id, "Удаление конфигов находится в разработке.", show_alert=True)
        bot.edit_message_reply_markup(chat_id=current_chat_id, message_id=current_message_id, reply_markup=manage_configs_keyboard())


    elif call.data == "admin_confirm_payments":
        if str(user_id) == str(ADMIN_ID):
            pending_card_payments = {pid: p_data for pid, p_data in payments_db.items() if p_data['status'] == 'pending' and p_data['screenshot_id'] and p_data['method'] == 'card'}
            
            if not pending_card_payments:
                bot.edit_message_text("Нет платежей (картой) со скриншотами, ожидающих подтверждения.", chat_id=current_chat_id, message_id=current_message_id, reply_markup=admin_keyboard())
                return
            
            for payment_id, p_data in pending_card_payments.items():
                user_payment = users_db.get(p_data['user_id'])
                if user_payment:
                    bot.send_photo(ADMIN_ID, p_data['screenshot_id'], 
                                   caption=f"Платеж ID: {payment_id}\n"
                                           f"От: @{user_payment.get('username', 'N/A')} (ID: {p_data['user_id']})\n"
                                           f"Сумма: {p_data['amount']} ₽\n"
                                           f"Период: {p_data['period'].replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}\n"
                                           f"Время: {p_data['timestamp']}",
                                   reply_markup=confirm_payments_keyboard(payment_id))
            bot.send_message(ADMIN_ID, "👆 Это все платежи (картой) со скриншотами, ожидающие подтверждения.", reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_confirm_"):
        if str(user_id) == str(ADMIN_ID):
            payment_id = call.data.replace("admin_confirm_", "")
            if payment_id in payments_db and payments_db[payment_id]['status'] == 'pending':
                payments_db[payment_id]['status'] = 'confirmed'
                
                target_user_id = payments_db[payment_id]['user_id']
                period_data = payments_db[payment_id]['period']
                
                if target_user_id in users_db:
                    update_user_subscription(target_user_id, period_data)
                    bot.send_message(target_user_id, 
                                     f"✅ Ваш платеж за подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')} подтвержден!\n"
                                     f"Теперь вы можете запросить конфиг в личном кабинете.",
                                     reply_markup=main_menu_keyboard(target_user_id))
                
                save_data('payments.json', payments_db)
                bot.edit_message_text(f"Платеж {payment_id} подтвержден.", chat_id=current_chat_id, message_id=current_message_id)
            else:
                bot.edit_message_text("Платеж уже обработан или не найден.", chat_id=current_chat_id, message_id=current_message_id)
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
                
                bot.edit_message_text(f"Платеж {payment_id} отклонен.", chat_id=current_chat_id, message_id=current_message_id)
            else:
                bot.edit_message_text("Платеж уже обработан или не найден.", chat_id=current_chat_id, message_id=current_message_id)
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
            
            bot.edit_message_text(message_text, chat_id=current_chat_id, message_id=current_message_id,
                                  parse_mode='Markdown', reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_edit_user":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(current_chat_id, "Введите ID пользователя, которого хотите изменить.")
            bot.register_next_step_handler(call.message, process_edit_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data == "admin_broadcast":
        if str(user_id) == str(ADMIN_ID):
            bot.send_message(current_chat_id, "Введите сообщение для рассылки всем пользователям.")
            bot.register_next_step_handler(call.message, process_broadcast_message)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = str(message.from_user.id)
    pending_payment = None
    for payment_id, p_data in payments_db.items():
        if p_data['user_id'] == user_id and p_data['status'] == 'pending' and p_data['screenshot_id'] is None and p_data['method'] == 'card':
            pending_payment = payment_id
            break
    
    if pending_payment:
        payments_db[pending_payment]['screenshot_id'] = message.photo[-1].file_id
        save_data('payments.json', payments_db)
        
        bot.send_message(message.chat.id, "Скриншот получен! Ожидайте подтверждения от администратора. "
                                         "Ваш платеж может быть подтвержден с задержкой.")
        
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

# --- ОБРАБОТКА ПЛАТЕЖЕЙ STARS (Pre-checkout и успешная оплата) ---
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    # Stars платежи не требуют подтверждения pre_checkout_query
    # Но для цифровых товаров, по документации Telegram, бот должен отвечать на pre_checkout_query
    # с is_ok=True, если товар готов к продаже.
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = str(message.from_user.id)
    invoice_payload = message.successful_payment.invoice_payload
    
    if invoice_payload in payments_db and payments_db[invoice_payload]['status'] == 'pending':
        payments_db[invoice_payload]['status'] = 'confirmed'
        
        period_data = payments_db[invoice_payload]['period']
        amount_stars = payments_db[invoice_payload]['amount'] # Сумма в Stars
        
        if user_id in users_db:
            update_user_subscription(user_id, period_data)
            
            bot.send_message(user_id, 
                             f"✅ Вы успешно оплатили {amount_stars} ⭐ за подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}!\n"
                             f"Теперь вы можете запросить конфиг в личном кабинете.",
                             reply_markup=main_menu_keyboard(user_id))
            
            # Уведомляем админа об успешной оплате Stars
            bot.send_message(ADMIN_ID, 
                             f"⭐ Успешная оплата Stars: {amount_stars} ⭐ от @{message.from_user.username} (ID: {user_id}) "
                             f"за {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}.\n"
                             f"Платеж ID: {invoice_payload}",
                             reply_markup=main_menu_keyboard(ADMIN_ID))

        save_data('payments.json', payments_db)
    else:
        bot.send_message(user_id, "Произошла ошибка при обработке вашего платежа. Пожалуйста, свяжитесь с поддержкой.",
                         reply_markup=main_menu_keyboard(user_id))

# --- ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЯ ПОДПИСКИ ПОЛЬЗОВАТЕЛЯ ---
def update_user_subscription(target_user_id, period_data):
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

# --- СЛЕДУЮЩИЕ ШАГИ ДЛЯ АДМИНКИ ---
def process_bulk_add_configs(message, period_to_add):
    user_id = str(message.from_user.id)
    if user_id != str(ADMIN_ID): return

    links = message.text.strip().split('\n')
    added_count = 0
    
    if period_to_add not in configs_db:
        configs_db[period_to_add] = []

    for link in links:
        link = link.strip()
        if link: # Проверяем, что ссылка не пустая
            new_config = {
                'name': f"Config for @{message.from_user.username}", # Имя конфига - имя пользователя админа для удобства
                'link': link,
                'is_used': False
            }
            configs_db[period_to_add].append(new_config)
            added_count += 1
    
    save_data('configs.json', configs_db)
    
    bot.send_message(user_id, f"Добавлено {added_count} конфигов на {period_to_add.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}.", 
                     reply_markup=admin_keyboard())

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
