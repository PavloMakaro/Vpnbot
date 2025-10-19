import telebot
from telebot import types
import logging
import json
import time
import os

# --- КОНСТАНТЫ ---
# НОВЫЙ ТОКЕН
BOT_TOKEN = "8217097426:AAEXU3BJ55Bkx-cfOEtRTxkPaOYC1zvRfO8" 
# ID администратора (ваш ID)
ADMIN_ID = 8320218178 
# Ваш ник для поддержки
SUPPORT_USERNAME = "@Gl1ch555"
# Номер карты для оплаты (Ozon Bank Makarov Pavel Alexandrovich)
CARD_NUMBER = "2204320690808227"
# Название банка и ФИО получателя
CARD_HOLDER_INFO = "Ozon Bank, Макаров Павел Александрович"
# Название сервера
VPN_SERVER_NAME = "X-Ray Server (Германия)"
# Файл для хранения данных (пользователи, конфиги)
DB_FILE = "db.json"
# Базовые цены и сроки (в секундах)
PRICES = {
    "1_month": {"price": 50, "days": 30, "duration": 30 * 24 * 3600},
    "2_months": {"price": 90, "days": 60, "duration": 60 * 24 * 3600},
    "3_months": {"price": 120, "days": 90, "duration": 90 * 24 * 3600},
}
# Награда за реферала
REFERRAL_BONUS_AMOUNT = 25  # рубли
REFERRAL_BONUS_DAYS = 7  # дни подписки

# --- ИНИЦИАЛИЗАЦИЯ ---
logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(BOT_TOKEN)

# --- УТИЛИТЫ ДЛЯ РАБОТЫ С DB ---
def load_db():
    """Загрузка данных из JSON файла"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"users": {}, "configs": {}, "pending_payments": {}}
    except json.JSONDecodeError:
        logging.error("Ошибка декодирования JSON в файле DB. Создан пустой шаблон.")
        return {"users": {}, "configs": {}, "pending_payments": {}}

def save_db(data):
    """Сохранение данных в JSON файл"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(user_id):
    """Получение данных пользователя, или создание нового, если не найден"""
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str not in db["users"]:
        db["users"][user_id_str] = {
            "subscription_end": 0,
            "referral_code": user_id_str,
            "referred_by": None,
            "balance": 0,
            "referrals_count": 0,
            "last_config_type": None, 
            "username": None
        }
        if user_id == ADMIN_ID:
             db["users"][user_id_str]["username"] = SUPPORT_USERNAME.strip('@')
        save_db(db)
    return db["users"][user_id_str]

def update_user(user_id, **kwargs):
    """Обновление данных пользователя"""
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str not in db["users"]:
        get_user(user_id)
    db["users"][user_id_str].update(kwargs)
    save_db(db)

def check_subscription(user_id):
    """Проверка активности подписки (True/False)"""
    user = get_user(user_id)
    return user["subscription_end"] > time.time()

def add_subscription(user_id, duration_seconds):
    """Продление или активация подписки"""
    user = get_user(user_id)
    current_end = user["subscription_end"]
    
    start_time = max(time.time(), current_end)
    new_end = start_time + duration_seconds
    
    update_user(user_id, subscription_end=new_end)
    return new_end

# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    """Основная клавиатура (Reply)"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🚀 Купить VPN", "👤 Личный кабинет")
    keyboard.row("❓ Поддержка", "🎁 Реферальная система")
    return keyboard

def get_admin_main_keyboard():
    """Основная админ-клавиатура (Reply)"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("✅ Неподтвержденные платежи")
    keyboard.row("🛠️ Управление конфигами")
    keyboard.row("🔙 Выйти из админки")
    return keyboard

def get_buy_options_keyboard():
    """Клавиатура с тарифами (Inline)"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for key, data in PRICES.items():
        text = f"{data['days']} дней - {data['price']} ₽"
        keyboard.add(types.InlineKeyboardButton(text, callback_data=f"buy_{key}"))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    return keyboard

def get_profile_keyboard(user_id):
    """Клавиатура личного кабинета (Inline)"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    if check_subscription(user_id):
        keyboard.add(types.InlineKeyboardButton("🔑 Запросить конфиг", callback_data="get_config"))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    return keyboard

def get_admin_config_menu_keyboard():
    """Меню управления конфигами (Inline)"""
    db = load_db()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for key, data in PRICES.items():
        days = data['days']
        status = "✅ Есть" if key in db["configs"] else "❌ Нет"
        text = f"{status} Конфиг на {days} дней"
        keyboard.add(types.InlineKeyboardButton(text, callback_data=f"admin_cfg_edit_{key}"))
        
    keyboard.add(types.InlineKeyboardButton("🔙 В админку", callback_data="admin_menu"))
    return keyboard


# --- ОБРАБОТЧИКИ СОСТОЯНИЙ (СТЕПЫ ДЛЯ TELEBOT) ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Обновление username пользователя
    username = message.from_user.username
    if username:
        update_user(user_id, username=username)

    # Проверка на реферальную ссылку
    if message.text.startswith('/start '):
        referred_by_id = message.text.split(' ')[1]
        
        user = get_user(user_id)
        if user["referred_by"] is None and referred_by_id != str(user_id):
            referrer = get_user(referred_by_id)
            if referrer:
                # Начисление бонуса рефереру
                new_balance = referrer["balance"] + REFERRAL_BONUS_AMOUNT
                new_end_time = add_subscription(referred_by_id, REFERRAL_BONUS_DAYS * 24 * 3600)
                new_referrals = referrer["referrals_count"] + 1
                
                update_user(referred_by_id, 
                            balance=new_balance,
                            referrals_count=new_referrals)
                
                update_user(user_id, referred_by=referred_by_id)
                
                bot.send_message(
                    referred_by_id,
                    f"🎉 **Отличная новость!** Пользователь @{username or user_id} "
                    f"зарегистрировался по вашей ссылке!\n"
                    f"Вам начислено **{REFERRAL_BONUS_AMOUNT} ₽** на баланс и **{REFERRAL_BONUS_DAYS} дней** подписки "
                    f"(до {time.strftime('%d.%m.%Y', time.localtime(new_end_time))})!",
                    parse_mode="Markdown"
                )

    # Приветственное сообщение
    text = (
        f"👋 **Привет, {message.from_user.first_name}!**\n"
        f"Я бот для продажи VPN ({VPN_SERVER_NAME}).\n"
        f"Выбери интересующий пункт меню ниже."
    )
    
    bot.send_message(user_id, text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['admin'])
def admin_start(message):
    """Обработчик команды /admin"""
    if message.from_user.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ У вас нет прав администратора.")
        
    bot.send_message(
        message.chat.id,
        "⚙️ **Добро пожаловать в Админку!**\n"
        "Выберите действие:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="Markdown"
    )

# --- ОБРАБОТЧИКИ МЕНЮ (Reply-кнопки) ---

@bot.message_handler(func=lambda message: message.text == "🚀 Купить VPN")
def buy_vpn_menu(message):
    """Меню покупки VPN"""
    text = (
        "💰 **Выберите тарифный план:**\n"
        f"Сервер: **{VPN_SERVER_NAME}**"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_buy_options_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "👤 Личный кабинет")
def personal_account(message):
    """Личный кабинет пользователя"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    is_active = check_subscription(user_id)
    status_text = "✅ Активна" if is_active else "❌ Неактивна"
    
    end_date_text = "—"
    if is_active:
        end_date_text = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(user["subscription_end"]))
        
    text = (
        "👤 **Ваш личный кабинет**\n"
        f"**Статус подписки:** {status_text}\n"
        f"**Окончание подписки:** {end_date_text}\n"
        f"**Ваш баланс (руб):** {user['balance']} ₽\n"
        "\n"
        "Выберите действие ниже:"
    )
    
    bot.send_message(message.chat.id, text, reply_markup=get_profile_keyboard(user_id), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "❓ Поддержка")
def support_info(message):
    """Информация о поддержке"""
    text = (
        "🆘 **Поддержка**\n"
        "По всем вопросам обращайтесь к администратору:\n"
        f"Ник: **{SUPPORT_USERNAME}**"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🎁 Реферальная система")
def referral_system(message):
    """Информация о реферальной системе"""
    user = get_user(message.from_user.id)
    
    referral_link = f"https://t.me/{bot.get_me().username}?start={user['referral_code']}"
    
    text = (
        "🎁 **Реферальная система**\n"
        "Приглашайте друзей и получайте бонусы!\n"
        f"За каждого приглашенного вы получаете:\n"
        f"  - **{REFERRAL_BONUS_AMOUNT} ₽** на баланс\n"
        f"  - **{REFERRAL_BONUS_DAYS} дней** подписки\n"
        f"\n"
        f"**Ваших рефералов:** {user['referrals_count']} чел.\n"
        f"**Ваша реферальная ссылка:** `{referral_link}`"
    )
    
    bot.send_message(message.chat.id, text, reply_markup=get_profile_keyboard(message.from_user.id), parse_mode="Markdown")

# Админка: Выход
@bot.message_handler(func=lambda message: message.text == "🔙 Выйти из админки" and message.from_user.id == ADMIN_ID)
def exit_admin(message):
    """Выход из админки"""
    bot.send_message(message.chat.id, "👋 Вы вышли из админки.", reply_markup=get_main_keyboard())

# Админка: Неподтвержденные платежи
@bot.message_handler(func=lambda message: message.text == "✅ Неподтвержденные платежи" and message.from_user.id == ADMIN_ID)
def admin_pending_payments(message):
    """Поиск пользователей с ожидающим платежом"""
    db = load_db()
    pending_payments = db["pending_payments"]
    
    if not pending_payments:
        return bot.send_message(message.chat.id, "ℹ️ Нет неподтвержденных платежей.")
        
    text = "⏳ **Ожидающие подтверждения платежи:**\n"
    for payment_id, data in pending_payments.items():
        user_id = data['user_id']
        username = data.get('username', 'N/A')
        plan_key = data['plan_key']
        
        text += (
            f"\n"
            f"ID платежа: `{payment_id}`\n"
            f"От: @{username} (ID: `{user_id}`)\n"
            f"Ожидает: {PRICES.get(plan_key, {}).get('days', '?')} дней за {PRICES.get(plan_key, {}).get('price', '?')} ₽\n"
            f"(Нужно найти скриншот выше и нажать кнопки)"
        )
        
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Админка: Управление конфигами
@bot.message_handler(func=lambda message: message.text == "🛠️ Управление конфигами" and message.from_user.id == ADMIN_ID)
def admin_config_menu(message):
    """Меню управления конфигами"""
    bot.send_message(
        message.chat.id,
        "🛠️ **Управление конфигами**\n"
        "Выберите тариф для настройки/изменения конфига:",
        reply_markup=get_admin_config_menu_keyboard(),
        parse_mode="Markdown"
    )

# --- ХЕНДЛЕРЫ ДЛЯ ПРОЦЕССА ОПЛАТЫ И КОНФИГОВ (TELEBOT) ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_buy_callback(call):
    """Начало процесса покупки"""
    plan_key = call.data.split('_')[1]
    
    if plan_key not in PRICES:
        return bot.answer_callback_query(call.id, "❌ Тариф не найден.", show_alert=True)
    
    plan_data = PRICES[plan_key]
    price = plan_data['price']
    
    # Сохраняем выбранный план в базе
    update_user(call.from_user.id, last_config_type=plan_key)
    
    text = (
        f"💳 **Оплата подписки на {plan_data['days']} дней ({price} ₽)**\n"
        "Для оплаты выполните перевод на сумму **{price} ₽** по следующим реквизитам:\n"
        f"**Номер карты:** `{CARD_NUMBER}`\n"
        f"**Банк/Получатель:** `{CARD_HOLDER_INFO}`\n"
        "\n"
        "⚠️ **Важно!** После перевода **ОБЯЗАТЕЛЬНО** отправьте скриншот подтверждения платежа в чат.\n"
        "После проверки администратором вам будет выдан конфиг."
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("✅ Я оплатил, готов отправить скриншот", callback_data=f"wait_scr_{plan_key}"))
    keyboard.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="main_menu"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('wait_scr_'))
def process_paid_and_waiting(call):
    """Пользователь готов отправить скриншот"""
    plan_key = call.data.split('_')[2]
    
    msg = bot.edit_message_text("🖼️ **Ожидаю скриншот перевода.**\nОтправьте его мне как *изображение* или *файл*.", 
                                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    # Регистрируем следующий шаг на прием скриншота, передавая plan_key
    bot.register_next_step_handler(msg, process_screenshot, plan_key=plan_key)
    bot.answer_callback_query(call.id)

def process_screenshot(message, plan_key):
    """Получение скриншота и отправка админу"""
    user_id = message.from_user.id
    price = PRICES[plan_key]['price']
    
    # Проверка, что это фото или документ
    if message.content_type not in ['photo', 'document']:
        msg = bot.send_message(user_id, "❌ Это не скриншот. Пожалуйста, отправьте его как изображение или файл.")
        return bot.register_next_step_handler(msg, process_screenshot, plan_key=plan_key)

    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    
    if not file_id:
        msg = bot.send_message(user_id, "❌ Не удалось получить файл. Попробуйте еще раз.")
        return bot.register_next_step_handler(msg, process_screenshot, plan_key=plan_key)
        
    # Создание уникального ID для платежа
    payment_id = f"{user_id}_{int(time.time())}"
    
    # Сохранение информации о платеже в базе
    db = load_db()
    db["pending_payments"][payment_id] = {
        "user_id": user_id,
        "username": message.from_user.username,
        "plan_key": plan_key,
        "file_id": file_id,
        "file_type": file_type
    }
    save_db(db)
    
    # Отправка админу на подтверждение
    admin_text = (
        f"🔔 **НОВЫЙ ПЛАТЕЖ!** (ID: `{payment_id}`)\n"
        f"**От:** Пользователь @{message.from_user.username or user_id} (ID: `{user_id}`)\n"
        f"**Тариф:** {PRICES[plan_key]['days']} дней\n"
        f"**Сумма:** {price} ₽"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_{payment_id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_decline_{payment_id}")
    )
    
    # Отправка скриншота
    if file_type == "photo":
        bot.send_photo(ADMIN_ID, file_id, caption=admin_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        bot.send_document(ADMIN_ID, file_id, caption=admin_text, reply_markup=keyboard, parse_mode="Markdown")
    
    # Уведомление пользователя
    bot.send_message(user_id,
        "✅ **Скриншот получен!**\n"
        "Ваш платеж отправлен на проверку администратору. "
        "Пожалуйста, ожидайте подтверждения (обычно занимает не более 5-10 минут)."
    )

@bot.callback_query_handler(func=lambda call: call.data == 'get_config')
def process_get_config(call):
    """Выдача конфига из личного кабинета"""
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if not check_subscription(user_id):
        return bot.answer_callback_query(call.id, "❌ Ваша подписка неактивна. Пожалуйста, продлите ее.", show_alert=True)
        
    config_key = user['last_config_type']
    db = load_db()
    
    if not config_key or config_key not in db["configs"]:
        return bot.answer_callback_query(call.id, "❌ Не удалось найти информацию о вашем конфиге. Обратитесь в поддержку.", show_alert=True)
        
    config_data = db["configs"][config_key]
    
    text = (
        f"🔑 **Ваш VPN-конфиг ({PRICES[config_key]['days']} дней)**\n"
        f"**Сервер:** {VPN_SERVER_NAME}\n"
        f"\n"
        f"🔗 **Ссылка на конфиг:** {config_data['link']}\n"
        f"📋 **Код (если требуется):** `{config_data['code']}`\n"
        f"\n"
        f"**Описание по установке:**\n"
        f"{config_data['description']}\n"
        f"\n"
        f"**Окончание подписки:** {time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(user['subscription_end']))}"
    )
    
    bot.send_message(user_id, text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
def process_main_menu(call):
    """Возврат в главное меню"""
    # Удаляем сообщение с кнопками, чтобы не было "висящих" клавиатур
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass # Игнорируем ошибку, если сообщение уже удалено
    send_welcome(call.message)
    bot.answer_callback_query(call.id)


# --- АДМИНКА: ОБРАБОТЧИКИ CALLBACKS (TELEBOT) ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_confirm_') and call.from_user.id == ADMIN_ID)
def admin_confirm_payment(call):
    """Подтверждение платежа администратором"""
    payment_id = call.data.split('_')[2]
        
    db = load_db()
    payment_data = db["pending_payments"].pop(payment_id, None)
    
    if not payment_data:
        bot.edit_message_caption(call.message.chat.id, call.message.message_id, 
                                 caption=call.message.caption + "\n\n**⚠️ ПЛАТЕЖ УЖЕ БЫЛ ОБРАБОТАН.**", 
                                 reply_markup=None, parse_mode="Markdown")
        return bot.answer_callback_query(call.id, "❌ Платеж уже обработан.", show_alert=True)

    user_id = payment_data['user_id']
    plan_key = payment_data['plan_key']
    
    # 1. Активация подписки
    duration = PRICES[plan_key]["duration"]
    new_end_time = add_subscription(user_id, duration)
    
    # 2. Обновление БД
    save_db(db)
    
    # 3. Отправка конфига пользователю (логика та же, что в get_config)
    config_data = db["configs"].get(plan_key)
    if config_data:
        config_text = (
            f"🎉 **Ваш платеж подтвержден!**\n"
            f"Подписка на **{PRICES[plan_key]['days']} дней** активирована.\n"
            f"\n"
            f"🔑 **Ваш VPN-конфиг ({PRICES[plan_key]['days']} дней)**\n"
            f"**Сервер:** {VPN_SERVER_NAME}\n"
            f"\n"
            f"🔗 **Ссылка на конфиг:** {config_data['link']}\n"
            f"📋 **Код (если требуется):** `{config_data['code']}`\n"
            f"\n"
            f"**Описание по установке:**\n"
            f"{config_data['description']}\n"
            f"\n"
            f"**Окончание подписки:** {time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(new_end_time))}"
        )
        try:
            bot.send_message(user_id, config_text, parse_mode="Markdown")
        except telebot.apihelper.ApiTelegramException:
             logging.error(f"Не удалось отправить сообщение пользователю {user_id}. Вероятно, он заблокировал бота.")
             bot.send_message(ADMIN_ID, f"⚠️ **Внимание!** Не удалось отправить конфиг пользователю `{user_id}` (возможно, заблокировал бота).")

    # 4. Обновление сообщения админа
    bot.edit_message_caption(call.message.chat.id, call.message.message_id, 
                             caption=call.message.caption + "\n\n**✅ ПЛАТЕЖ ПОДТВЕРЖДЕН и КОНФИГ ВЫДАН.**",
                             reply_markup=None,
                             parse_mode="Markdown")
    bot.answer_callback_query(call.id, "✅ Платеж подтвержден. Подписка активирована и конфиг отправлен.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_decline_') and call.from_user.id == ADMIN_ID)
def admin_decline_payment(call):
    """Отклонение платежа администратором"""
    payment_id = call.data.split('_')[2]
    
    db = load_db()
    payment_data = db["pending_payments"].pop(payment_id, None)
    save_db(db)
    
    if not payment_data:
        bot.edit_message_caption(call.message.chat.id, call.message.message_id, 
                                 caption=call.message.caption + "\n\n**⚠️ ПЛАТЕЖ УЖЕ БЫЛ ОБРАБОТАН.**", 
                                 reply_markup=None, parse_mode="Markdown")
        return bot.answer_callback_query(call.id, "❌ Платеж уже обработан.", show_alert=True)
        
    user_id = payment_data['user_id']
    
    # Уведомление пользователя
    try:
        bot.send_message(
            user_id,
            "❌ **Ваш платеж не подтвержден.**\n"
            "Возможно, скриншот был нечетким, или перевод не поступил.\n"
            f"Пожалуйста, свяжитесь с поддержкой: **{SUPPORT_USERNAME}**",
            parse_mode="Markdown"
        )
    except telebot.apihelper.ApiTelegramException:
         logging.error(f"Не удалось отправить сообщение пользователю {user_id}. Вероятно, он заблокировал бота.")

    # Обновление сообщения админа
    bot.edit_message_caption(call.message.chat.id, call.message.message_id, 
                             caption=call.message.caption + "\n\n**❌ ПЛАТЕЖ ОТКЛОНЕН.**",
                             reply_markup=None,
                             parse_mode="Markdown")
    bot.answer_callback_query(call.id, "❌ Платеж отклонен. Пользователь уведомлен.")

# --- АДМИНКА: КОНФИГИ (TELEBOT) ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_cfg_edit_') and call.from_user.id == ADMIN_ID)
def admin_cfg_start_edit(call):
    """Начало процесса редактирования конфига"""
    config_key = call.data.split('_')[-1]
    plan_data = PRICES[config_key]
    
    msg = bot.edit_message_text(
        f"🔗 **Настройка конфига на {plan_data['days']} дней**\n"
        "Шаг 1/3: **Отправьте ссылку на VPN-конфиг** (например, ссылку на файл или подписку).",
        call.message.chat.id, call.message.message_id
    )
    
    # Регистрируем следующий шаг: получение ссылки
    bot.register_next_step_handler(msg, admin_cfg_get_link, config_key=config_key)
    bot.answer_callback_query(call.id)

def admin_cfg_get_link(message, config_key):
    """Получение ссылки на конфиг"""
    config_link = message.text
    
    msg = bot.send_message(message.chat.id, 
        "📋 Шаг 2/3: **Отправьте код конфига** (QR-код или ключ). "
        "Если код не нужен, отправьте `НЕТ`."
    )
    
    # Регистрируем следующий шаг: получение кода
    bot.register_next_step_handler(msg, admin_cfg_get_code, config_key=config_key, config_link=config_link)

def admin_cfg_get_code(message, config_key, config_link):
    """Получение кода конфига"""
    code = message.text.upper()
    config_code = "—" if code == "НЕТ" else code
    
    msg = bot.send_message(message.chat.id, 
        "📝 Шаг 3/3: **Отправьте описание по установке/использованию конфига.** "
        "Это будет инструкция для пользователя."
    )
    
    # Регистрируем следующий шаг: получение описания и сохранение
    bot.register_next_step_handler(msg, admin_cfg_save, config_key=config_key, config_link=config_link, config_code=config_code)

def admin_cfg_save(message, config_key, config_link, config_code):
    """Получение описания и сохранение конфига"""
    config_description = message.text
    
    db = load_db()
    db["configs"][config_key] = {
        "link": config_link,
        "code": config_code,
        "description": config_description,
    }
    save_db(db)
    
    plan_data = PRICES[config_key]
    bot.send_message(
        message.chat.id,
        f"✅ **Конфиг на {plan_data['days']} дней успешно обновлен!**\n"
        f"**Ссылка:** {config_link}\n"
        f"**Код:** {config_code}\n"
        f"**Описание:** {config_description}",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="Markdown"
    )

# --- ЗАПУСК БОТА ---
if __name__ == '__main__':
    logging.info("Бот запускается...")
    # Инициализация DB и данных админа
    load_db() 
    
    # В telebot используется polling
    try:
        bot.polling(none_stop=True, interval=1)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")

