import telebot
from telebot import types
import json
import time
import datetime
import threading
import os
import subprocess

# --- КОНСТАНТЫ ---
TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY'
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
        
        # Создаем инвойс для оплаты Stars
        try:
            prices = [types.LabeledPrice(label=f"VPN подписка на {period_data.replace('_', ' ')}", amount=amount * 100)]  # В звездах (1 звезда = 100)
            
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
                # Ищем конфиги, которые соответствуют периоду подписки или подходят для любого периода
                for period, configs_list in configs_db.items():
                    available_configs.extend(configs_list)

                if available_configs:
                    # Выдаем первый доступный конфиг
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
                              f"💡 **Как это работает:**\n"
                              f"• Вы получаете уникальную реферальную ссылку\n"
                              f"• Делитесь ей с друзьями и знакомыми\n"
                              f"• Когда кто-то регистрируется по вашей ссылке и покупает подписку:\n"
                              f"  🔹 Вы получаете {REFERRAL_BONUS_RUB} ₽ на баланс\n"
                              f"  🔹 И {REFERRAL_BONUS_DAYS} дней к вашей активной подписке\n\n"
                              f"💰 **Ваши бонусы:**\n"
                              f"• Рефералов приглашено: {referrals_count}\n"
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
                        message_text += f"  {i+1}. Имя: {config['name']}, Код: `{config['code']}` (ID: {i})\n"
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

# --- ОБРАБОТЧИК ПРЕДОПЛАТЫ (Telegram Stars) ---
@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    user_id = str(message.from_user.id)
    payment_info = message.successful_payment
    
    # Извлекаем период из invoice_payload
    payload_parts = payment_info.invoice_payload.split('_')
    if len(payload_parts) >= 4:
        period_data = payload_parts[2] + '_' + payload_parts[3]
        
        # Создаем запись о платеже
        payment_id = generate_payment_id()
        payments_db[payment_id] = {
            'user_id': user_id,
            'amount': payment_info.total_amount / 100,  # Конвертируем обратно из звезд
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

            bot.send_message(user_id, 
                             f"✅ Ваш платеж за подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')} подтвержден!\n"
                             f"Ваша подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                             f"Можете запросить конфиг в личном кабинете.",
                             reply_markup=main_menu_keyboard(user_id))
        
        # Уведомляем админа
        bot.send_message(ADMIN_ID, 
                         f"✅ Успешная оплата Stars: {payment_info.total_amount / 100} Stars\n"
                         f"От: @{message.from_user.username} (ID: {user_id})\n"
                         f"Период: {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}")

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
                               f"Период: {payments_db[pending_payment]['period'].replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}",
                       reply_markup=confirm_payments_keyboard(pending_payment))

# --- ФУНКЦИИ АДМИНКИ ---
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
            # Генерируем имя на основе username пользователя
            username = message.from_user.username if message.from_user.username else 'user'
            config_name = f"{username} {len(configs_db[period]) + 1}"
            
            config_data = {
                'name': config_name,
                'image': None,  # Можно добавить позже
                'code': f"{username}_{len(configs_db[period]) + 1}",
                'link': link
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

def process_edit_user_id(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    target_user_id = message.text.strip()
    if target_user_id in users_db:
        bot.send_message(message.chat.id, f"Редактирование пользователя {target_user_id}:\n"
                                          f"Текущий баланс: {users_db[target_user_id].get('balance', 0)} ₽\n"
                                          f"Текущая подписка до: {users_db[target_user_id].get('subscription_end', 'Нет')}\n\n"
                                          f"Введите новое значение баланса (только число):")
        bot.register_next_step_handler(message, process_edit_user_balance, target_user_id)
    else:
        bot.send_message(message.chat.id, "❌ Пользователь не найден.")

def process_edit_user_balance(message, target_user_id):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        new_balance = int(message.text.strip())
        users_db[target_user_id]['balance'] = new_balance
        
        bot.send_message(message.chat.id, f"Баланс пользователя {target_user_id} обновлен до {new_balance} ₽.\n"
                                          f"Введите новую дату окончания подписки (в формате ДД.ММ.ГГГГ ЧЧ:ММ или 'нет' для удаления):")
        bot.register_next_step_handler(message, process_edit_user_subscription, target_user_id)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат баланса. Введите только число.")

def process_edit_user_subscription(message, target_user_id):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    new_subscription = message.text.strip()
    if new_subscription.lower() == 'нет':
        users_db[target_user_id]['subscription_end'] = None
        bot.send_message(message.chat.id, f"✅ Подписка пользователя {target_user_id} удалена.")
    else:
        try:
            new_end = datetime.datetime.strptime(new_subscription, '%d.%m.%Y %H:%M')
            users_db[target_user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
            bot.send_message(message.chat.id, f"✅ Подписка пользователя {target_user_id} установлена до {new_end.strftime('%d.%m.%Y %H:%M')}.")
        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверный формат даты. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")
    
    save_data('users.json', users_db)

def process_broadcast_message(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    broadcast_text = message.text
    sent_count = 0
    failed_count = 0
    
    for user_id in users_db.keys():
        try:
            bot.send_message(user_id, f"📢 Рассылка от администратора:\n\n{broadcast_text}")
            sent_count += 1
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
            failed_count += 1
    
    bot.send_message(message.chat.id, f"✅ Рассылка завершена:\n"
                                      f"Отправлено: {sent_count}\n"
                                      f"Не удалось: {failed_count}")

# --- ФУНКЦИЯ ОСТАНОВКИ БОТА ПЕРЕД ОБНОВЛЕНИЕМ ---
def stop_bot_before_update():
    """Останавливает бота перед обновлением"""
    print("Останавливаю бота для обновления...")
    bot.stop_polling()
    print("Бот остановлен. Можно обновлять код.")

# --- ЗАПУСК БОТА ---
if __name__ == "__main__":
    print("Бот запущен...")
    try:
        bot.polling(none_stop=True, interval=0, timeout=60)
    except KeyboardInterrupt:
        print("Бот остановлен пользователем.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        # Автоматическая остановка при ошибке для возможного перезапуска
        stop_bot_before_update()
