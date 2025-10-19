import logging
import json
import time
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# --- КОНСТАНТЫ ---
# Токен бота
BOT_TOKEN = "8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY"
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
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- FSM (Finite State Machine) для пошаговых действий ---
class Payment(StatesGroup):
    """Состояния для процесса оплаты"""
    waiting_for_screenshot = State()
    waiting_for_admin_confirmation = State()
    
class AdminConfig(StatesGroup):
    """Состояния для добавления/удаления конфигов в админке"""
    waiting_for_config_link = State()
    waiting_for_config_code = State()
    waiting_for_config_desc = State()
    waiting_for_config_action = State() # Для указания, какой именно конфиг добавляем/удаляем

# --- УТИЛИТЫ ДЛЯ РАБОТЫ С DB ---
def load_db():
    """Загрузка данных из JSON файла"""
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": {}, "configs": {}}
    except json.JSONDecodeError:
        logging.error("Ошибка декодирования JSON в файле DB. Создан пустой шаблон.")
        return {"users": {}, "configs": {}}

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
            "payment_pending": False,
            "referrals_count": 0,
            "last_config_type": None, # Последний купленный тариф
        }
        save_db(db)
    return db["users"][user_id_str]

def update_user(user_id, **kwargs):
    """Обновление данных пользователя"""
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str not in db["users"]:
        get_user(user_id) # Создаем, если нет
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
    
    # Если подписка еще активна, добавляем к текущему концу, иначе к текущему моменту
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
    
    # Кнопка запроса конфига активна, только если есть активная подписка
    if check_subscription(user_id):
        keyboard.add(types.InlineKeyboardButton("🔑 Запросить конфиг", callback_data="get_config"))
        
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    return keyboard

def get_referral_keyboard(user_id):
    """Клавиатура реферальной системы (Inline)"""
    user = get_user(user_id)
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    referral_link = f"https://t.me/{bot.me.username}?start={user['referral_code']}"
    keyboard.add(types.InlineKeyboardButton("🔗 Моя реферальная ссылка", url=referral_link))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    return keyboard

def get_admin_main_keyboard():
    """Основная админ-клавиатура (Reply)"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("✅ Неподтвержденные платежи")
    keyboard.row("🛠️ Управление конфигами")
    keyboard.row("🔙 Выйти из админки")
    return keyboard

def get_admin_config_menu_keyboard():
    """Меню управления конфигами (Inline)"""
    db = load_db()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    # Кнопки для добавления/изменения конфигов
    for key, data in PRICES.items():
        days = data['days']
        status = "✅ Есть" if key in db["configs"] else "❌ Нет"
        text = f"{status} Конфиг на {days} дней"
        keyboard.add(types.InlineKeyboardButton(text, callback_data=f"admin_cfg_edit_{key}"))
        
    keyboard.add(types.InlineKeyboardButton("🔙 В админку", callback_data="admin_menu"))
    return keyboard


# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message_handler(commands=['start'], state='*')
async def send_welcome(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Проверка на реферальную ссылку
    if message.get_args():
        referred_by_id = message.get_args()
        
        # Только если пользователь новый и не сам себя пригласил
        user = get_user(user_id)
        if user["referred_by"] is None and referred_by_id != str(user_id):
            referrer = get_user(referred_by_id)
            if referrer:
                # Начисление бонуса рефереру
                update_user(referred_by_id, 
                            balance=referrer["balance"] + REFERRAL_BONUS_AMOUNT,
                            subscription_end=add_subscription(referred_by_id, REFERRAL_BONUS_DAYS * 24 * 3600),
                            referrals_count=referrer["referrals_count"] + 1)
                
                # Запись в базу приглашенного
                update_user(user_id, referred_by=referred_by_id)
                
                await bot.send_message(
                    referred_by_id,
                    f"🎉 **Отличная новость!** Пользователь @{message.from_user.username or user_id} "
                    f"зарегистрировался по вашей ссылке!\n"
                    f"Вам начислено **{REFERRAL_BONUS_AMOUNT} ₽** на баланс и **{REFERRAL_BONUS_DAYS} дней** подписки!",
                    parse_mode="Markdown"
                )

    # Приветственное сообщение
    text = (
        f"👋 **Привет, {message.from_user.first_name}!**\n"
        f"Я бот для продажи VPN ({VPN_SERVER_NAME}).\n"
        f"Выбери интересующий пункт меню ниже."
    )
    
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message_handler(commands=['admin'], state='*')
async def admin_start(message: types.Message):
    """Обработчик команды /admin"""
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ У вас нет прав администратора.")
        
    await message.answer(
        "⚙️ **Добро пожаловать в Админку!**\n"
        "Выберите действие:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message_handler(text="🔙 Выйти из админки", user_id=ADMIN_ID, state='*')
async def exit_admin(message: types.Message):
    """Выход из админки"""
    await message.answer("👋 Вы вышли из админки.", reply_markup=get_main_keyboard())

# --- ОБРАБОТЧИКИ МЕНЮ (Reply-кнопки) ---

@dp.message_handler(text="🚀 Купить VPN", state='*')
async def buy_vpn_menu(message: types.Message):
    """Меню покупки VPN"""
    text = (
        "💰 **Выберите тарифный план:**\n"
        f"Сервер: **{VPN_SERVER_NAME}**"
    )
    await message.answer(text, reply_markup=get_buy_options_keyboard(), parse_mode="Markdown")

@dp.message_handler(text="👤 Личный кабинет", state='*')
async def personal_account(message: types.Message):
    """Личный кабинет пользователя"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # Статус подписки
    is_active = check_subscription(user_id)
    status_text = "✅ Активна" if is_active else "❌ Неактивна"
    
    # Дата окончания
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
    
    await message.answer(text, reply_markup=get_profile_keyboard(user_id), parse_mode="Markdown")

@dp.message_handler(text="❓ Поддержка", state='*')
async def support_info(message: types.Message):
    """Информация о поддержке"""
    text = (
        "🆘 **Поддержка**\n"
        "По всем вопросам обращайтесь к администратору:\n"
        f"Ник: **{SUPPORT_USERNAME}**"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message_handler(text="🎁 Реферальная система", state='*')
async def referral_system(message: types.Message):
    """Информация о реферальной системе"""
    user = get_user(message.from_user.id)
    
    text = (
        "🎁 **Реферальная система**\n"
        "Приглашайте друзей и получайте бонусы!\n"
        f"За каждого приглашенного вы получаете:\n"
        f"  - **{REFERRAL_BONUS_AMOUNT} ₽** на баланс\n"
        f"  - **{REFERRAL_BONUS_DAYS} дней** подписки\n"
        f"\n"
        f"**Ваших рефералов:** {user['referrals_count']} чел.\n"
        "Используйте вашу уникальную ссылку, чтобы пригласить друга:"
    )
    
    await message.answer(text, reply_markup=get_referral_keyboard(message.from_user.id), parse_mode="Markdown")

# --- ОБРАБОТЧИКИ INLINE-КНОПОК (CALLBACKS) ---

@dp.callback_query_handler(lambda c: c.data == 'main_menu', state='*')
async def process_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.finish()
    await callback_query.message.delete()
    await send_welcome(callback_query.message)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'), state='*')
async def process_buy_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало процесса покупки"""
    plan_key = callback_query.data.split('_')[1]
    
    if plan_key not in PRICES:
        return await callback_query.answer("❌ Тариф не найден.", show_alert=True)
    
    plan_data = PRICES[plan_key]
    price = plan_data['price']
    
    # Сохраняем выбранный план
    update_user(callback_query.from_user.id, last_config_type=plan_key)
    await state.update_data(plan_key=plan_key, price=price)
    
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
    keyboard.add(types.InlineKeyboardButton("✅ Я оплатил, жду подтверждения", callback_data="paid_and_waiting"))
    keyboard.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="main_menu"))
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'paid_and_waiting', state='*')
async def process_paid_and_waiting(callback_query: types.CallbackQuery, state: FSMContext):
    """Пользователь готов отправить скриншот"""
    await Payment.waiting_for_screenshot.set()
    await callback_query.message.edit_text("🖼️ **Ожидаю скриншот перевода.**\nОтправьте его мне как *изображение* или *файл*.")
    await callback_query.answer()

@dp.message_handler(content_types=['photo', 'document'], state=Payment.waiting_for_screenshot)
async def process_screenshot(message: types.Message, state: FSMContext):
    """Получение скриншота и отправка админу"""
    user_id = message.from_user.id
    user_data = await state.get_data()
    plan_key = user_data.get('plan_key')
    price = user_data.get('price')
    
    # Получаем ID файла (для фото - последнее, для документа - сам документ)
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    
    if not file_id:
        return await message.answer("❌ Не удалось получить файл. Попробуйте еще раз.")
        
    # Помечаем платеж как ожидающий
    update_user(user_id, payment_pending=True)
    
    # Отправка админу на подтверждение
    admin_text = (
        f"🔔 **НОВЫЙ ПЛАТЕЖ!**\n"
        f"**От:** Пользователь @{message.from_user.username or user_id} (ID: `{user_id}`)\n"
        f"**Тариф:** {PRICES[plan_key]['days']} дней\n"
        f"**Сумма:** {price} ₽\n"
        f"**Скриншот:**"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_{user_id}_{plan_key}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_decline_{user_id}")
    )
    
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
    await bot.send_photo(ADMIN_ID, file_id, reply_markup=keyboard)
    
    await message.answer(
        "✅ **Скриншот получен!**\n"
        "Ваш платеж отправлен на проверку администратору. "
        "Пожалуйста, ожидайте подтверждения (обычно занимает не более 5-10 минут)."
    )
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'get_config', state='*')
async def process_get_config(callback_query: types.CallbackQuery):
    """Выдача конфига из личного кабинета"""
    user_id = callback_query.from_user.id
    user = get_user(user_id)
    
    if not check_subscription(user_id):
        await callback_query.answer("❌ Ваша подписка неактивна. Пожалуйста, продлите ее.", show_alert=True)
        return
        
    config_key = user['last_config_type']
    db = load_db()
    
    if not config_key or config_key not in db["configs"]:
        await callback_query.answer("❌ Не удалось найти информацию о вашем конфиге. Обратитесь в поддержку.", show_alert=True)
        return
        
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
    
    await callback_query.message.answer(text, parse_mode="Markdown")
    await callback_query.answer()

# --- АДМИНКА: ПЛАТЕЖИ ---

@dp.message_handler(text="✅ Неподтвержденные платежи", user_id=ADMIN_ID, state='*')
async def admin_pending_payments(message: types.Message):
    """Поиск пользователей с ожидающим платежом"""
    db = load_db()
    pending_users = [
        uid for uid, udata in db["users"].items() if udata.get("payment_pending")
    ]
    
    if not pending_users:
        return await message.answer("ℹ️ Нет неподтвержденных платежей.")
        
    text = "⏳ **Ожидающие подтверждения платежи:**\n"
    for uid in pending_users:
        user = db["users"][uid]
        text += (
            f"\n"
            f"ID: `{uid}`\n"
            f"Ник: @{user.get('username', 'N/A')}\n"
            f"Ожидает: Конфиг на {PRICES.get(user.get('last_config_type', 'N/A'), {}).get('days', '?')} дней\n"
            f"(Нужно найти скриншот выше в чате и подтвердить)"
        )
        
    await message.answer(text, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith('admin_confirm_'), user_id=ADMIN_ID, state='*')
async def admin_confirm_payment(callback_query: types.CallbackQuery):
    """Подтверждение платежа администратором"""
    try:
        _, _, user_id, plan_key = callback_query.data.split('_')
        user_id = int(user_id)
    except ValueError:
        return await callback_query.answer("❌ Ошибка в данных callback'а.", show_alert=True)
        
    db = load_db()
    if str(user_id) not in db["users"]:
        return await callback_query.answer("❌ Пользователь не найден.", show_alert=True)
        
    user = db["users"][str(user_id)]
    if not user.get("payment_pending"):
        await callback_query.message.edit_reply_markup(None)
        return await callback_query.answer("❌ Платеж уже обработан или не ожидал подтверждения.", show_alert=True)
        
    # 1. Активация подписки
    duration = PRICES[plan_key]["duration"]
    new_end_time = add_subscription(user_id, duration)
    
    # 2. Обнуление флага ожидания
    update_user(user_id, payment_pending=False)
    
    # 3. Отправка конфига пользователю
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
        await bot.send_message(user_id, config_text, parse_mode="Markdown")
    else:
        await bot.send_message(user_id, 
                               f"🎉 **Ваш платеж подтвержден!** Подписка на **{PRICES[plan_key]['days']} дней** активирована.\n"
                               f"⚠️ **Внимание!** Конфиг не был выдан, так как он не настроен в админке. Обратитесь в поддержку.", 
                               parse_mode="Markdown")
        
    # 4. Обновление сообщения админа
    await callback_query.message.edit_caption(
        callback_query.message.caption + "\n\n**✅ ПЛАТЕЖ ПОДТВЕРЖДЕН и КОНФИГ ВЫДАН.**",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await callback_query.answer("✅ Платеж подтвержден. Подписка активирована и конфиг отправлен.")

@dp.callback_query_handler(lambda c: c.data.startswith('admin_decline_'), user_id=ADMIN_ID, state='*')
async def admin_decline_payment(callback_query: types.CallbackQuery):
    """Отклонение платежа администратором"""
    try:
        _, _, user_id = callback_query.data.split('_')
        user_id = int(user_id)
    except ValueError:
        return await callback_query.answer("❌ Ошибка в данных callback'а.", show_alert=True)
        
    user = get_user(user_id)
    if not user.get("payment_pending"):
        await callback_query.message.edit_reply_markup(None)
        return await callback_query.answer("❌ Платеж уже обработан или не ожидал подтверждения.", show_alert=True)
        
    # Обнуление флага ожидания
    update_user(user_id, payment_pending=False)
    
    # Уведомление пользователя
    await bot.send_message(
        user_id,
        "❌ **Ваш платеж не подтвержден.**\n"
        "Возможно, скриншот был нечетким, или перевод не поступил.\n"
        f"Пожалуйста, свяжитесь с поддержкой: **{SUPPORT_USERNAME}**",
        parse_mode="Markdown"
    )
    
    # Обновление сообщения админа
    await callback_query.message.edit_caption(
        callback_query.message.caption + "\n\n**❌ ПЛАТЕЖ ОТКЛОНЕН.**",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await callback_query.answer("❌ Платеж отклонен. Пользователь уведомлен.")

# --- АДМИНКА: КОНФИГИ ---

@dp.message_handler(text="🛠️ Управление конфигами", user_id=ADMIN_ID, state='*')
async def admin_config_menu(message: types.Message):
    """Меню управления конфигами"""
    await message.answer(
        "🛠️ **Управление конфигами**\n"
        "Выберите тариф для настройки/изменения конфига:",
        reply_markup=get_admin_config_menu_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data.startswith('admin_cfg_edit_'), user_id=ADMIN_ID, state='*')
async def admin_cfg_start_edit(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало процесса редактирования конфига"""
    config_key = callback_query.data.split('_')[-1]
    
    if config_key not in PRICES:
        return await callback_query.answer("❌ Тариф не найден.", show_alert=True)
        
    plan_data = PRICES[config_key]
    
    await state.update_data(current_config_key=config_key)
    
    await AdminConfig.waiting_for_config_link.set()
    await callback_query.message.edit_text(
        f"🔗 **Настройка конфига на {plan_data['days']} дней**\n"
        "Шаг 1/3: **Отправьте ссылку на VPN-конфиг** (например, ссылку на файл или подписку)."
    )
    await callback_query.answer()

@dp.message_handler(state=AdminConfig.waiting_for_config_link)
async def admin_cfg_get_link(message: types.Message, state: FSMContext):
    """Получение ссылки на конфиг"""
    await state.update_data(config_link=message.text)
    await AdminConfig.waiting_for_config_code.set()
    await message.answer(
        "📋 Шаг 2/3: **Отправьте код конфига** (QR-код или ключ). "
        "Если код не нужен, отправьте `НЕТ`."
    )

@dp.message_handler(state=AdminConfig.waiting_for_config_code)
async def admin_cfg_get_code(message: types.Message, state: FSMContext):
    """Получение кода конфига"""
    code = message.text.upper()
    await state.update_data(config_code="—" if code == "НЕТ" else code)
    await AdminConfig.waiting_for_config_desc.set()
    await message.answer(
        "📝 Шаг 3/3: **Отправьте описание по установке/использованию конфига.** "
        "Это будет инструкция для пользователя."
    )

@dp.message_handler(state=AdminConfig.waiting_for_config_desc)
async def admin_cfg_get_desc(message: types.Message, state: FSMContext):
    """Получение описания и сохранение конфига"""
    data = await state.get_data()
    config_key = data['current_config_key']
    
    db = load_db()
    db["configs"][config_key] = {
        "link": data['config_link'],
        "code": data['config_code'],
        "description": message.text,
    }
    save_db(db)
    
    await state.finish()
    
    plan_data = PRICES[config_key]
    await message.answer(
        f"✅ **Конфиг на {plan_data['days']} дней успешно обновлен!**\n"
        f"**Ссылка:** {data['config_link']}\n"
        f"**Код:** {data['config_code']}\n"
        f"**Описание:** {message.text}",
        reply_markup=get_admin_main_keyboard()
    )


# --- ЗАПУСК БОТА ---
if __name__ == '__main__':
    # Создаем db.json, если не существует
    load_db() 
    
    # Устанавливаем админу username в базе (для удобства отображения платежей)
    try:
        admin_info = get_user(ADMIN_ID)
        if admin_info.get('username') != SUPPORT_USERNAME.strip('@'):
            update_user(ADMIN_ID, username=SUPPORT_USERNAME.strip('@'))
    except Exception as e:
        logging.error(f"Не удалось обновить username админа: {e}")
        
    executor.start_polling(dp, skip_updates=True)
