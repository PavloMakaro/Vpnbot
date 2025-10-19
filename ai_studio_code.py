import logging
import sqlite3
import datetime
import os
import random
import json # Для хранения конфигов как JSON
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_context import FSMContext
from aiogram.contrib.fsm_context.storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# --- КОНФИГУРАЦИЯ БОТА ---
BOT_TOKEN = "8217097426:AAEXU3BJ55Bkx-cfOEtRTxkPaOYC1zvRfO8"
ADMIN_USERNAME = "@Gl1ch555"
ADMIN_ID = 8320218178  # Ваш фактический Telegram ID
CARD_NUMBER = "2204320690808227" # Номер карты для перевода (Ozon Bank Makarov Pavel Alexandrovich)

# Цены за VPN в рублях
PRICES = {
    "1_month": 50,
    "2_month": 90,
    "3_month": 130,
}

# Дни подписки
SUBSCRIPTION_DAYS = {
    "1_month": 30,
    "2_month": 60,
    "3_month": 90,
}

# Реферальная система
REFERRAL_BONUS_AMOUNT = 25  # Рублей на баланс
REFERRAL_BONUS_DAYS = 7     # Дней к подписке

# Путь к базе данных
DB_NAME = "vpn_bot.db"

# --- ИНИЦИАЛИЗАЦИЯ БОТА И ДИСПАТЧЕРА ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- СОСТОЯНИЯ ДЛЯ FSM ---
class PurchaseStates(StatesGroup):
    waiting_for_screenshot = State()

class AdminStates(StatesGroup):
    waiting_for_message_to_users = State()
    waiting_for_config_tariff = State() # Для выбора тарифа при добавлении конфига
    waiting_for_config_text = State()
    waiting_for_config_image_or_url = State()
    waiting_for_config_url = State()

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            balance REAL DEFAULT 0.0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER, -- ID пользователя, который пригласил
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date TIMESTAMP,
            tariff TEXT NOT NULL, -- '1_month', '2_month', '3_month'
            config_data TEXT,    -- JSON-строка с данными конфига {text, image_id, url}
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            tariff TEXT NOT NULL,
            screenshot_id TEXT, -- File ID скриншота
            status TEXT DEFAULT 'pending', -- 'pending', 'confirmed', 'rejected'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_by INTEGER, -- Admin ID
            confirmed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vpn_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tariff TEXT NOT NULL, -- '1_month', '2_month', '3_month'
            config_text TEXT,    -- Сам текст конфига
            config_image_id TEXT, -- File ID изображения, если есть
            config_url TEXT,     -- Ссылка на подписку/файл, если есть
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(telegram_id, username, referred_by=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    referral_code = generate_referral_code()
    cursor.execute("INSERT INTO users (telegram_id, username, referral_code, referred_by) VALUES (?, ?, ?, ?)",
                   (telegram_id, username, referral_code, referred_by))
    conn.commit()
    conn.close()
    return get_user(telegram_id)

def get_user_by_referral_code(referral_code):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users WHERE referral_code = ?", (referral_code,))
    user_id = cursor.fetchone()
    conn.close()
    return user_id[0] if user_id else None

def update_user_balance(telegram_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, telegram_id))
    conn.commit()
    conn.close()

def create_payment(user_id, amount, tariff, screenshot_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO payments (user_id, amount, tariff, screenshot_id) VALUES (?, ?, ?, ?)",
                   (user_id, amount, tariff, screenshot_id))
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return payment_id

def get_payment(payment_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    payment = cursor.fetchone()
    conn.close()
    return payment

def get_pending_payments():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT p.*, u.username FROM payments p JOIN users u ON p.user_id = u.telegram_id WHERE p.status = 'pending'")
    payments = cursor.fetchall()
    conn.close()
    return payments

def update_payment_status(payment_id, status, admin_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if status == 'confirmed':
        cursor.execute("UPDATE payments SET status = ?, confirmed_by = ?, confirmed_at = CURRENT_TIMESTAMP WHERE id = ?",
                       (status, admin_id, payment_id))
    else:
        cursor.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))
    conn.commit()
    conn.close()

def add_subscription(user_id, tariff, config_data_json):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    days = SUBSCRIPTION_DAYS.get(tariff, 0)
    
    active_sub = get_active_subscription(user_id)
    if active_sub:
        current_end_date_str = active_sub[3]
        if isinstance(current_end_date_str, str):
            try:
                current_end_date = datetime.datetime.strptime(current_end_date_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                current_end_date = datetime.datetime.strptime(current_end_date_str, "%Y-%m-%d %H:%M:%S")
        else:
            current_end_date = current_end_date_str

        new_end_date = current_end_date + datetime.timedelta(days=days)
        cursor.execute("UPDATE subscriptions SET end_date = ?, tariff = ?, config_data = ? WHERE id = ?",
                       (new_end_date, tariff, config_data_json, active_sub[0]))
    else:
        end_date = datetime.datetime.now() + datetime.timedelta(days=days)
        cursor.execute("INSERT INTO subscriptions (user_id, tariff, end_date, config_data) VALUES (?, ?, ?, ?)",
                       (user_id, tariff, end_date, config_data_json))
    conn.commit()
    conn.close()

def get_active_subscription(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    cursor.execute("SELECT * FROM subscriptions WHERE user_id = ? AND end_date > ? AND is_active = TRUE ORDER BY end_date DESC LIMIT 1",
                   (user_id, now))
    subscription = cursor.fetchone()
    conn.close()
    return subscription

def get_all_subscriptions(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions WHERE user_id = ? ORDER BY end_date DESC", (user_id,))
    subscriptions = cursor.fetchall()
    conn.close()
    return subscriptions

def extend_subscription(user_id, days):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    active_sub = get_active_subscription(user_id)
    if active_sub:
        current_end_date_str = active_sub[3]
        if isinstance(current_end_date_str, str):
            try:
                current_end_date = datetime.datetime.strptime(current_end_date_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                current_end_date = datetime.datetime.strptime(current_end_date_str, "%Y-%m-%d %H:%M:%S")
        else:
            current_end_date = current_end_date_str
            
        new_end_date = current_end_date + datetime.timedelta(days=days)
        cursor.execute("UPDATE subscriptions SET end_date = ? WHERE id = ?",
                       (new_end_date, active_sub[0]))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users]

# --- Функции для управления VPN конфигами ---
def add_vpn_config(tariff, config_text=None, config_image_id=None, config_url=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO vpn_configs (tariff, config_text, config_image_id, config_url) VALUES (?, ?, ?, ?)",
                   (tariff, config_text, config_image_id, config_url))
    conn.commit()
    conn.close()

def get_active_vpn_configs(tariff):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, config_text, config_image_id, config_url FROM vpn_configs WHERE tariff = ? AND is_active = TRUE", (tariff,))
    configs = cursor.fetchall()
    conn.close()
    # Возвращаем список словарей для удобства
    return [{"id": c[0], "config_text": c[1], "config_image_id": c[2], "config_url": c[3]} for c in configs]

def get_all_vpn_configs():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, tariff, config_text, config_image_id, config_url, is_active FROM vpn_configs ORDER BY tariff, id")
    configs = cursor.fetchall()
    conn.close()
    return configs

def get_vpn_config_by_id(config_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, tariff, config_text, config_image_id, config_url, is_active FROM vpn_configs WHERE id = ?", (config_id,))
    config = cursor.fetchone()
    conn.close()
    return config

def toggle_vpn_config_status(config_id, current_status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    new_status = not current_status
    cursor.execute("UPDATE vpn_configs SET is_active = ? WHERE id = ?", (new_status, config_id))
    conn.commit()
    conn.close()
    return new_status

def delete_vpn_config(config_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vpn_configs WHERE id = ?", (config_id,))
    conn.commit()
    conn.close()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def generate_referral_code():
    import uuid
    return str(uuid.uuid4())[:8] # Короткий уникальный код

def get_tariff_name(tariff_key):
    return tariff_key.replace('_', ' ').capitalize()

# --- КЛАВИАТУРЫ ---
def get_main_menu_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🚀 Купить VPN", callback_data="buy_vpn"),
        types.InlineKeyboardButton("👤 Личный кабинет", callback_data="my_cabinet"),
        types.InlineKeyboardButton(f"📞 Поддержка {ADMIN_USERNAME}", url=f"https://t.me/{ADMIN_USERNAME[1:]}"),
        types.InlineKeyboardButton("🤝 Реферальная система", callback_data="referral_system"),
        types.InlineKeyboardButton("ℹ️ О боте и помощь", callback_data="about")
    )
    return keyboard

def get_purchase_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        types.InlineKeyboardButton(f"1 месяц ({PRICES['1_month']} ₽)", callback_data="select_tariff:1_month"),
        types.InlineKeyboardButton(f"2 месяца ({PRICES['2_month']} ₽)", callback_data="select_tariff:2_month"),
        types.InlineKeyboardButton(f"3 месяца ({PRICES['3_month']} ₽)", callback_data="select_tariff:3_month")
    )
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main_menu"))
    return keyboard

def get_admin_payment_keyboard(payment_id):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_payment:{payment_id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_payment:{payment_id}")
    )
    return keyboard

def get_cabinet_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🗓 Мои подписки", callback_data="show_my_subscriptions"),
        types.InlineKeyboardButton("⚙️ Получить конфиг", callback_data="get_my_config"),
        types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main_menu")
    )
    return keyboard

def get_admin_menu_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("👀 Проверить платежи", callback_data="admin_check_payments"),
        types.InlineKeyboardButton("➕ Управление конфигами", callback_data="admin_manage_configs"),
        types.InlineKeyboardButton("✉️ Сделать рассылку", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("📊 Статистика (скоро)", callback_data="admin_stats")
    )
    return keyboard

def get_referral_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🔗 Моя реферальная ссылка", callback_data="show_referral_link"),
        types.InlineKeyboardButton("💰 Мои бонусы", callback_data="show_referral_balance"),
        types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main_menu")
    )
    return keyboard

def get_admin_config_management_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("➕ Добавить новый конфиг", callback_data="admin_add_config"),
        types.InlineKeyboardButton("📋 Просмотреть/Редактировать конфиги", callback_data="admin_list_configs"),
        types.InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_panel_back")
    )
    return keyboard

def get_admin_config_tariff_select_keyboard(action_prefix):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        types.InlineKeyboardButton("1 месяц", callback_data=f"{action_prefix}:1_month"),
        types.InlineKeyboardButton("2 месяца", callback_data=f"{action_prefix}:2_month"),
        types.InlineKeyboardButton("3 месяца", callback_data=f"{action_prefix}:3_month")
    )
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_manage_configs"))
    return keyboard

def get_admin_config_actions_keyboard(config_id, is_active):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    status_text = "Деактивировать" if is_active else "Активировать"
    keyboard.add(
        types.InlineKeyboardButton(status_text, callback_data=f"admin_toggle_config:{config_id}"),
        types.InlineKeyboardButton("🗑 Удалить", callback_data=f"admin_delete_config:{config_id}")
    )
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад к списку", callback_data="admin_list_configs"))
    return keyboard

# --- ОБРАБОТЧИКИ КОМАНД И СООБЩЕНИЙ ---

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish() # Сбрасываем все состояния
    referrer_id = None
    if len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
        referrer_id = get_user_by_referral_code(referral_code)

    user = get_user(message.from_user.id)
    if not user:
        user = create_user(message.from_user.id, message.from_user.username, referrer_id)
        if referrer_id:
            # Начисляем бонус пригласившему
            update_user_balance(referrer_id, REFERRAL_BONUS_AMOUNT)
            extend_subscription(referrer_id, REFERRAL_BONUS_DAYS) # Продлеваем подписку, если есть
            try:
                await bot.send_message(referrer_id, f"🎉 Ваш реферал @{message.from_user.username if message.from_user.username else message.from_user.full_name} зарегистрировался! Вам начислено {REFERRAL_BONUS_AMOUNT} руб. на баланс и {REFERRAL_BONUS_DAYS} дней к подписке.")
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление рефереру {referrer_id}: {e}")

    await message.answer(f"Привет, {message.from_user.full_name}! 👋\nДобро пожаловать в VPN Master Bot! Обеспечьте себе безопасный и быстрый интернет.",
                         reply_markup=get_main_menu_keyboard())

@dp.message_handler(commands=['admin'], user_id=ADMIN_ID)
async def cmd_admin(message: types.Message):
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=get_admin_menu_keyboard())

@dp.callback_query_handler(text="back_to_main_menu")
async def back_to_main_menu(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_text(f"Привет, {call.from_user.full_name}! 👋\nДобро пожаловать в VPN Master Bot! Обеспечьте себе безопасный и быстрый интернет.",
                                 reply_markup=get_main_menu_keyboard())
    await call.answer()

@dp.callback_query_handler(text="buy_vpn")
async def buy_vpn(call: types.CallbackQuery):
    await call.message.edit_text("Выберите тарифный план:", reply_markup=get_purchase_keyboard())
    await call.answer()

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('select_tariff:'))
async def select_tariff(call: types.CallbackQuery, state: FSMContext):
    tariff = call.data.split(':')[1]
    price = PRICES.get(tariff)

    await state.update_data(selected_tariff=tariff, selected_price=price)
    
    await call.message.edit_text(f"Для оплаты {price} руб. за тариф '{get_tariff_name(tariff)}' переведите деньги на карту: `{CARD_NUMBER}`\n\n"
                                 "После перевода **ОБЯЗАТЕЛЬНО** пришлите скриншот чека в следующем сообщении. Я проверю платеж и активирую подписку.",
                                 parse_mode="Markdown",
                                 reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад к тарифам", callback_data="buy_vpn")))
    await PurchaseStates.waiting_for_screenshot.set()
    await call.answer()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=PurchaseStates.waiting_for_screenshot)
async def process_screenshot(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    tariff = user_data.get("selected_tariff")
    price = user_data.get("selected_price")
    screenshot_id = message.photo[-1].file_id

    if not tariff or not price:
        await message.answer("Произошла ошибка при обработке тарифа. Пожалуйста, попробуйте снова, нажав /start.",
                             reply_markup=get_main_menu_keyboard())
        await state.finish()
        return

    payment_id = create_payment(message.from_user.id, price, tariff, screenshot_id)

    # Уведомляем администратора о новом платеже
    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=screenshot_id,
            caption=f"🔔 Новый платеж ожидает подтверждения!\n\n"
                    f"Пользователь: @{message.from_user.username if message.from_user.username else message.from_user.id} (ID: {message.from_user.id})\n"
                    f"Тариф: {get_tariff_name(tariff)}\n"
                    f"Сумма: {price} руб.\n\n"
                    f"Проверьте скриншот и подтвердите/отклоните платеж.",
            reply_markup=get_admin_payment_keyboard(payment_id)
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление админу о платеже: {e}")
        await message.answer("Произошла ошибка при уведомлении администратора. Пожалуйста, свяжитесь с поддержкой.",
                             reply_markup=get_main_menu_keyboard())
        await state.finish()
        return

    await message.answer("✅ Ваш скриншот получен и ожидает подтверждения администратором. Ожидайте уведомления!",
                         reply_markup=get_main_menu_keyboard())
    await state.finish() # Завершаем состояние ожидания скриншота

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('admin_confirm_payment:'), user_id=ADMIN_ID)
async def admin_confirm_payment(call: types.CallbackQuery, state: FSMContext):
    payment_id = int(call.data.split(':')[1])
    payment = get_payment(payment_id)

    if payment and payment[5] == 'pending': # payment[5] - status
        user_id = payment[1]
        tariff = payment[3]

        active_configs = get_active_vpn_configs(tariff)
        if not active_configs:
            await call.message.answer(f"Ошибка: Нет активных конфигов для тарифа {get_tariff_name(tariff)}. Добавьте их через админку.")
            await call.answer()
            return

        # Выбираем случайный активный конфиг
        selected_config = random.choice(active_configs)
        config_data_json = json.dumps(selected_config) # Сохраняем все данные конфига в подписке

        # Обновляем статус платежа в базе
        update_payment_status(payment_id, 'confirmed', call.from_user.id)
        # Добавляем/продлеваем подписку
        add_subscription(user_id, tariff, config_data_json)

        # Отправляем конфиг пользователю
        try:
            caption_text = f"🎉 Платеж подтвержден! Ваша подписка на {get_tariff_name(tariff)} активирована.\n\n"
            if selected_config['config_text']:
                caption_text += f"Вот ваш VPN-конфиг:\n`{selected_config['config_text']}`\n\n"
            if selected_config['config_url']:
                caption_text += f"Ссылка для подписки/доступа: {selected_config['config_url']}\n\n"
            caption_text += "Спасибо за использование!"
            
            if selected_config['config_image_id']:
                await bot.send_photo(user_id, photo=selected_config['config_image_id'], caption=caption_text, parse_mode="Markdown")
            else:
                await bot.send_message(user_id, caption_text, parse_mode="Markdown")

            username_from_db = get_user(user_id)[2] if get_user(user_id) else "Неизвестный пользователь"
            await call.message.edit_caption(caption=f"✅ Платеж пользователя @{username_from_db} (ID: {user_id}) за {get_tariff_name(tariff)} подтвержден. Конфиг отправлен.",
                                           reply_markup=None)
            await call.answer("Платеж подтвержден и конфиг отправлен пользователю.", show_alert=True)
        except Exception as e:
            logging.error(f"Не удалось отправить конфиг пользователю {user_id}: {e}")
            username_from_db = get_user(user_id)[2] if get_user(user_id) else "Неизвестный пользователь"
            await call.message.edit_caption(caption=f"⚠️ Ошибка отправки конфига пользователю @{username_from_db} (ID: {user_id}). Платеж подтвержден, но конфиг не отправлен. Проверьте логи.",
                                           reply_markup=None)
            await call.answer("Произошла ошибка при отправке конфига.", show_alert=True)
    else:
        await call.answer("Этот платеж уже был обработан или не существует.", show_alert=True)
        if call.message.reply_markup:
            await call.message.edit_reply_markup(reply_markup=None)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('admin_reject_payment:'), user_id=ADMIN_ID)
async def admin_reject_payment(call: types.CallbackQuery, state: FSMContext):
    payment_id = int(call.data.split(':')[1])
    payment = get_payment(payment_id)

    if payment and payment[5] == 'pending': # payment[5] - status
        user_id = payment[1]
        update_payment_status(payment_id, 'rejected', call.from_user.id)
        
        try:
            await bot.send_message(user_id, "❌ К сожалению, ваш платеж не был подтвержден администратором. Пожалуйста, свяжитесь с поддержкой, если возникли вопросы.")
        except Exception as e:
            logging.error(f"Не удалось уведомить пользователя {user_id} об отклонении платежа: {e}")
        
        username_from_db = get_user(user_id)[2] if get_user(user_id) else "Неизвестный пользователь"
        await call.message.edit_caption(caption=f"❌ Платеж пользователя @{username_from_db} (ID: {user_id}) за {get_tariff_name(payment[3])} отклонен.",
                                       reply_markup=None)
        await call.answer("Платеж отклонен.", show_alert=True)
    else:
        await call.answer("Этот платеж уже был обработан или не существует.", show_alert=True)
        if call.message.reply_markup:
            await call.message.edit_reply_markup(reply_markup=None)

@dp.callback_query_handler(text="my_cabinet")
async def my_cabinet(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if not user:
        await call.message.answer("Пожалуйста, нажмите /start, чтобы зарегистрироваться.")
        await call.answer()
        return

    active_sub = get_active_subscription(call.from_user.id)
    if active_sub:
        end_date_str = active_sub[3]
        if isinstance(end_date_str, str):
            try:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
        else:
            end_date = end_date_str

        remaining_days = (end_date - datetime.datetime.now()).days
        if remaining_days < 0:
            remaining_days = 0
        
        message_text = f"Ваш личный кабинет:\n\n" \
                       f"🗓 Активная подписка до: `{end_date.strftime('%d.%m.%Y %H:%M')}`\n" \
                       f"Осталось: `{remaining_days} дней`\n" \
                       f"Тариф: `{get_tariff_name(active_sub[4])}`"
    else:
        message_text = "Ваш личный кабинет:\n\nУ вас пока нет активных подписок. Купите VPN!"

    await call.message.edit_text(message_text, parse_mode="Markdown", reply_markup=get_cabinet_keyboard())
    await call.answer()

@dp.callback_query_handler(text="get_my_config")
async def get_my_config(call: types.CallbackQuery):
    active_sub = get_active_subscription(call.from_user.id)
    if active_sub:
        config_data_json = active_sub[5]
        try:
            selected_config = json.loads(config_data_json)
        except json.JSONDecodeError:
            await call.message.answer("К сожалению, данные вашего конфига повреждены. Свяжитесь с поддержкой.")
            await call.answer()
            return
        
        caption_text = f"Ваш текущий VPN-конфиг для тарифа {get_tariff_name(active_sub[4])}:\n\n"
        if selected_config.get('config_text'):
            caption_text += f"`{selected_config['config_text']}`\n\n"
        if selected_config.get('config_url'):
            caption_text += f"Ссылка для подписки/доступа: {selected_config['config_url']}\n\n"
        caption_text += "Приятного использования!"
        
        if selected_config.get('config_image_id'):
            await bot.send_photo(call.from_user.id, photo=selected_config['config_image_id'], caption=caption_text, parse_mode="Markdown")
        else:
            await bot.send_message(call.from_user.id, caption_text, parse_mode="Markdown")

    else:
        await call.message.answer("У вас нет активных подписок. Купите VPN, чтобы получить конфиг!",
                                 reply_markup=get_purchase_keyboard())
    await call.answer()

@dp.callback_query_handler(text="show_my_subscriptions")
async def show_my_subscriptions(call: types.CallbackQuery):
    subscriptions = get_all_subscriptions(call.from_user.id)
    if subscriptions:
        message_text = "Ваши подписки:\n\n"
        for sub in subscriptions:
            end_date_str = sub[3]
            if isinstance(end_date_str, str):
                try:
                    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
            else:
                end_date = end_date_str
            
            status = "Активна" if end_date > datetime.datetime.now() else "Истекла"
            message_text += f"- Тариф: `{get_tariff_name(sub[4])}`\n" \
                            f"  До: `{end_date.strftime('%d.%m.%Y %H:%M')}` ({status})\n\n"
    else:
        message_text = "У вас пока нет оформленных подписок."

    await call.message.edit_text(message_text, parse_mode="Markdown", reply_markup=get_cabinet_keyboard())
    await call.answer()

@dp.callback_query_handler(text="about")
async def about_bot(call: types.CallbackQuery):
    message_text = "ℹ️ **О боте и помощь**\n\n" \
                   "Этот бот позволяет приобрести доступ к VPN-серверам.\n\n" \
                   "**Как это работает:**\n" \
                   "1. Выбираете тариф и оплачиваете его переводом на карту.\n" \
                   "2. Отправляете скриншот чека об оплате.\n" \
                   "3. Администратор проверяет платеж и выдает вам VPN-конфиг.\n" \
                   "4. Используйте полученные данные (текст, изображение, ссылка) для подключения к VPN.\n\n" \
                   "**Возникли вопросы?** Свяжитесь с поддержкой через раздел 'Поддержка'."
    await call.message.edit_text(message_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())
    await call.answer()

@dp.callback_query_handler(text="referral_system")
async def referral_system(call: types.CallbackQuery):
    await call.message.edit_text(f"Приглашайте друзей и получайте бонусы!\n\n"
                                 f"Когда ваш друг купит VPN по вашей ссылке, вы получите 💰 {REFERRAL_BONUS_AMOUNT} руб. на баланс и 🗓 {REFERRAL_BONUS_DAYS} дней к подписке!",
                                 reply_markup=get_referral_keyboard())
    await call.answer()

@dp.callback_query_handler(text="show_referral_link")
async def show_referral_link(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user and user[4]: # user[4] - referral_code
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        referral_link = f"https://t.me/{bot_username}?start={user[4]}"
        await call.message.edit_text(f"Ваша реферальная ссылка:\n`{referral_link}`\n\n"
                                     "Отправьте ее друзьям!", parse_mode="Markdown",
                                     reply_markup=get_referral_keyboard())
    else:
        await call.message.answer("У вас нет реферального кода. Пожалуйста, свяжитесь с поддержкой.")
    await call.answer()

@dp.callback_query_handler(text="show_referral_balance")
async def show_referral_balance(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user:
        balance = user[3] # user[3] - balance
        await call.message.edit_text(f"Ваш текущий баланс бонусов: `{balance} руб.`\n\n"
                                     "Эти средства вы можете использовать для продления подписки (обратитесь в поддержку)!", parse_mode="Markdown",
                                     reply_markup=get_referral_keyboard())
    else:
        await call.message.answer("Не удалось получить информацию о балансе. Пожалуйста, нажмите /start.")
    await call.answer()


# --- АДМИН-ФУНКЦИИ ---
@dp.callback_query_handler(text="admin_panel_back", user_id=ADMIN_ID)
async def admin_panel_back(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_text("Добро пожаловать в админ-панель!", reply_markup=get_admin_menu_keyboard())
    await call.answer()

@dp.callback_query_handler(text="admin_check_payments", user_id=ADMIN_ID)
async def admin_check_payments(call: types.CallbackQuery):
    pending_payments = get_pending_payments()
    if not pending_payments:
        await call.message.edit_text("Нет новых платежей, ожидающих подтверждения.", reply_markup=get_admin_menu_keyboard())
        await call.answer()
        return

    for payment in pending_payments:
        payment_id = payment[0]
        user_id = payment[1]
        amount = payment[2]
        tariff = payment[3]
        screenshot_id = payment[4]
        username = payment[9] if payment[9] else "N/A"

        await bot.send_photo(
            chat_id=call.from_user.id,
            photo=screenshot_id,
            caption=f"🔔 Новый платеж ожидает подтверждения!\n\n"
                    f"Пользователь: @{username} (ID: {user_id})\n"
                    f"Тариф: {get_tariff_name(tariff)}\n"
                    f"Сумма: {amount} руб.\n\n"
                    f"Проверьте скриншот и подтвердите/отклоните платеж.",
            reply_markup=get_admin_payment_keyboard(payment_id)
        )
    await call.answer("Отправлены все ожидающие платежи.")

@dp.callback_query_handler(text="admin_broadcast", user_id=ADMIN_ID)
async def admin_broadcast_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введите текст сообщения для рассылки всем пользователям:")
    await AdminStates.waiting_for_message_to_users.set()
    await call.answer()

@dp.message_handler(state=AdminStates.waiting_for_message_to_users, user_id=ADMIN_ID)
async def admin_broadcast_message(message: types.Message, state: FSMContext):
    broadcast_text = message.text
    all_users = get_all_users()
    sent_count = 0
    failed_count = 0

    for user_id in all_users:
        try:
            await bot.send_message(user_id, broadcast_text)
            sent_count += 1
        except Exception as e:
            logging.error(f"Не удалось отправить рассылку пользователю {user_id}: {e}")
            failed_count += 1
    
    await message.answer(f"Рассылка завершена.\nОтправлено сообщений: {sent_count}\nНе удалось отправить: {failed_count}",
                         reply_markup=get_admin_menu_keyboard())
    await state.finish()

# --- Управление конфигами ---
@dp.callback_query_handler(text="admin_manage_configs", user_id=ADMIN_ID)
async def admin_manage_configs(call: types.CallbackQuery):
    await call.message.edit_text("Управление VPN-конфигами:", reply_markup=get_admin_config_management_keyboard())
    await call.answer()

@dp.callback_query_handler(text="admin_add_config", user_id=ADMIN_ID)
async def admin_add_config_start(call: types.CallbackQuery):
    await call.message.edit_text("Выберите тариф, для которого вы хотите добавить конфиг:",
                                 reply_markup=get_admin_config_tariff_select_keyboard("admin_select_config_tariff_add"))
    await call.answer()

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('admin_select_config_tariff_add:'), user_id=ADMIN_ID)
async def admin_select_config_tariff_add(call: types.CallbackQuery, state: FSMContext):
    tariff = call.data.split(':')[1]
    await state.update_data(current_config_tariff=tariff)
    await call.message.edit_text(f"Вы выбрали тариф: {get_tariff_name(tariff)}.\n\n"
                                 "Теперь пришлите **текст конфига**. Если текста нет, напишите `-` (дефис).")
    await AdminStates.waiting_for_config_text.set()
    await call.answer()

@dp.message_handler(state=AdminStates.waiting_for_config_text, user_id=ADMIN_ID)
async def admin_get_config_text(message: types.Message, state: FSMContext):
    config_text = message.text
    if config_text == "-":
        config_text = None
    
    await state.update_data(current_config_text=config_text)
    await message.answer("Отлично! Теперь пришлите **изображение-QR-код** для конфига (если есть) или **ссылку на подписку/конфиг**. "
                         "Если изображения нет, а есть только ссылка - просто отправьте ссылку. Если ничего нет - напишите `-` (дефис).")
    await AdminStates.waiting_for_config_image_or_url.set()

@dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.TEXT], state=AdminStates.waiting_for_config_image_or_url, user_id=ADMIN_ID)
async def admin_get_config_image_or_url(message: types.Message, state: FSMContext):
    config_image_id = None
    config_url = None
    
    if message.content_type == types.ContentType.PHOTO:
        config_image_id = message.photo[-1].file_id
        await state.update_data(current_config_image_id=config_image_id)
        await message.answer("Изображение получено. Теперь пришлите **ссылку на подписку/конфиг** (если есть). Если ссылки нет - напишите `-` (дефис).")
        await AdminStates.waiting_for_config_url.set()
    elif message.content_type == types.ContentType.TEXT:
        if message.text == "-":
            # Ни изображения, ни ссылки
            user_data = await state.get_data()
            tariff = user_data.get("current_config_tariff")
            config_text = user_data.get("current_config_text")
            
            add_vpn_config(tariff, config_text=config_text)
            await message.answer(f"Новый конфиг для тарифа {get_tariff_name(tariff)} успешно добавлен (только текст).",
                                 reply_markup=get_admin_config_management_keyboard())
            await state.finish()
        else: # Пользователь прислал ссылку вместо изображения
            config_url = message.text
            user_data = await state.get_data()
            tariff = user_data.get("current_config_tariff")
            config_text = user_data.get("current_config_text")

            add_vpn_config(tariff, config_text=config_text, config_url=config_url)
            await message.answer(f"Новый конфиг для тарифа {get_tariff_name(tariff)} успешно добавлен (текст и ссылка).",
                                 reply_markup=get_admin_config_management_keyboard())
            await state.finish()
    else:
        await message.answer("Пожалуйста, пришлите изображение, ссылку или `-` (дефис).")

@dp.message_handler(state=AdminStates.waiting_for_config_url, user_id=ADMIN_ID)
async def admin_get_config_url(message: types.Message, state: FSMContext):
    config_url = None
    if message.text != "-":
        config_url = message.text
    
    user_data = await state.get_data()
    tariff = user_data.get("current_config_tariff")
    config_text = user_data.get("current_config_text")
    config_image_id = user_data.get("current_config_image_id")

    add_vpn_config(tariff, config_text=config_text, config_image_id=config_image_id, config_url=config_url)
    await message.answer(f"Новый конфиг для тарифа {get_tariff_name(tariff)} успешно добавлен.",
                         reply_markup=get_admin_config_management_keyboard())
    await state.finish()

@dp.callback_query_handler(text="admin_list_configs", user_id=ADMIN_ID)
async def admin_list_configs(call: types.CallbackQuery):
    configs = get_all_vpn_configs()
    if not configs:
        await call.message.edit_text("Пока нет добавленных конфигов.", reply_markup=get_admin_config_management_keyboard())
        await call.answer()
        return

    message_text = "Список конфигов:\n\n"
    for config in configs:
        config_id, tariff, config_text, config_image_id, config_url, is_active = config
        status = "✅ Активен" if is_active else "❌ Неактивен"
        message_text += f"ID: `{config_id}` | Тариф: `{get_tariff_name(tariff)}` | Статус: {status}\n"
        if config_text:
            message_text += f"  Текст: `{'...' + config_text[-20:] if len(config_text) > 20 else config_text}`\n"
        if config_url:
            message_text += f"  URL: `{config_url}`\n"
        if config_image_id:
            message_text += f"  Изображение: Есть\n"
        message_text += f"  /view_config_{config_id}\n\n" # Быстрая ссылка для просмотра/редактирования

    await call.message.edit_text(message_text, parse_mode="Markdown", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_manage_configs")))
    await call.answer()

@dp.message_handler(commands=lambda msg: msg.startswith('view_config_'), user_id=ADMIN_ID)
async def admin_view_single_config(message: types.Message):
    config_id = int(message.text.split('_')[2])
    config = get_vpn_config_by_id(config_id)

    if not config:
        await message.answer("Конфиг не найден.")
        return
    
    config_id, tariff, config_text, config_image_id, config_url, is_active = config
    
    status_text = "✅ Активен" if is_active else "❌ Неактивен"
    message_text = f"**Детали конфига (ID: `{config_id}`)**\n\n" \
                   f"Тариф: `{get_tariff_name(tariff)}`\n" \
                   f"Статус: {status_text}\n"

    if config_text:
        message_text += f"\n**Текст конфига:**\n`{config_text}`\n"
    if config_url:
        message_text += f"\n**Ссылка:**\n`{config_url}`\n"
    
    if config_image_id:
        await bot.send_photo(message.from_user.id, photo=config_image_id, caption=message_text, parse_mode="Markdown",
                             reply_markup=get_admin_config_actions_keyboard(config_id, is_active))
    else:
        await message.answer(message_text, parse_mode="Markdown",
                             reply_markup=get_admin_config_actions_keyboard(config_id, is_active))

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('admin_toggle_config:'), user_id=ADMIN_ID)
async def admin_toggle_config(call: types.CallbackQuery):
    config_id = int(call.data.split(':')[1])
    config = get_vpn_config_by_id(config_id)
    if config:
        new_status = toggle_vpn_config_status(config_id, config[5]) # config[5] - is_active
        await call.message.edit_reply_markup(reply_markup=get_admin_config_actions_keyboard(config_id, new_status))
        await call.answer(f"Статус конфига изменен на {'активный' if new_status else 'неактивный'}.", show_alert=True)
        # Обновляем сообщение с деталями конфига
        config_id, tariff, config_text, config_image_id, config_url, is_active = get_vpn_config_by_id(config_id)
        status_text = "✅ Активен" if is_active else "❌ Неактивен"
        message_text = f"**Детали конфига (ID: `{config_id}`)**\n\n" \
                       f"Тариф: `{get_tariff_name(tariff)}`\n" \
                       f"Статус: {status_text}\n"
        if config_text: message_text += f"\n**Текст конфига:**\n`{config_text}`\n"
        if config_url: message_text += f"\n**Ссылка:**\n`{config_url}`\n"
        if call.message.caption: # Если это было фото, меняем caption
            await call.message.edit_caption(caption=message_text, parse_mode="Markdown", reply_markup=get_admin_config_actions_keyboard(config_id, is_active))
        else: # Если обычное сообщение
            await call.message.edit_text(message_text, parse_mode="Markdown", reply_markup=get_admin_config_actions_keyboard(config_id, is_active))
    else:
        await call.answer("Конфиг не найден.", show_alert=True)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('admin_delete_config:'), user_id=ADMIN_ID)
async def admin_delete_config(call: types.CallbackQuery):
    config_id = int(call.data.split(':')[1])
    delete_vpn_config(config_id)
    await call.message.edit_text(f"Конфиг с ID `{config_id}` удален.", parse_mode="Markdown", reply_markup=get_admin_config_management_keyboard())
    await call.answer("Конфиг удален.", show_alert=True)

# --- ЗАПУСК БОТА ---
async def on_startup(dp):
    init_db()
    logging.info("Database initialized.")

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
