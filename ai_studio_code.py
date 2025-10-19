import logging
import sqlite3
import datetime
import os
import random
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_context import FSMContext
from aiogram.contrib.fsm_context.storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# --- КОНФИГУРАЦИЯ БОТА ---
BOT_TOKEN = "8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY"
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
CONFIGS_FOLDER = "configs" # Папка для конфигов VPN

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
            config_path TEXT,
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

def add_subscription(user_id, tariff, config_path):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    days = SUBSCRIPTION_DAYS.get(tariff, 0)
    
    # Получаем текущую активную подписку
    active_sub = get_active_subscription(user_id)
    if active_sub:
        # Если есть, продлеваем ее
        current_end_date_str = active_sub[3]
        # Проверяем формат даты, если это строка, парсим
        if isinstance(current_end_date_str, str):
            try:
                current_end_date = datetime.datetime.strptime(current_end_date_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                # Если другой формат, можно попробовать другой или обработать ошибку
                current_end_date = datetime.datetime.strptime(current_end_date_str, "%Y-%m-%d %H:%M:%S")
        else: # Если уже datetime object
            current_end_date = current_end_date_str

        new_end_date = current_end_date + datetime.timedelta(days=days)
        cursor.execute("UPDATE subscriptions SET end_date = ?, tariff = ? WHERE id = ?",
                       (new_end_date, tariff, active_sub[0]))
    else:
        # Если нет активной подписки, создаем новую
        end_date = datetime.datetime.now() + datetime.timedelta(days=days)
        cursor.execute("INSERT INTO subscriptions (user_id, tariff, end_date, config_path) VALUES (?, ?, ?, ?)",
                       (user_id, tariff, end_date, config_path))
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

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def generate_referral_code():
    import uuid
    return str(uuid.uuid4())[:8] # Короткий уникальный код

def get_random_config_path(tariff_key):
    # Пример: configs/1_month_config_1.conf
    # Ищем все файлы, начинающиеся с `tariff_key`
    possible_configs = [f for f in os.listdir(CONFIGS_FOLDER) if f.startswith(f"{tariff_key}_config")]
    if not possible_configs:
        return None
    return os.path.join(CONFIGS_FOLDER, random.choice(possible_configs))

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
    
    await call.message.edit_text(f"Для оплаты {price} руб. за тариф '{tariff.replace('_', ' ')}' переведите деньги на карту: `{CARD_NUMBER}`\n\n"
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
                    f"Тариф: {tariff.replace('_', ' ')}\n"
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

        config_path = get_random_config_path(tariff)
        if not config_path:
            await call.message.answer(f"Ошибка: Не найден конфиг для тарифа {tariff}. Пожалуйста, добавьте конфиги в папку 'configs/'.")
            await call.answer()
            return

        # Обновляем статус платежа в базе
        update_payment_status(payment_id, 'confirmed', call.from_user.id)
        # Добавляем/продлеваем подписку
        add_subscription(user_id, tariff, config_path)

        # Отправляем конфиг пользователю
        try:
            with open(config_path, 'rb') as f:
                await bot.send_document(user_id, f, caption=f"🎉 Платеж подтвержден! Ваша подписка на {tariff.replace('_', ' ')} активирована. Вот ваш VPN-конфиг:")
            # Уведомляем админа об успешном подтверждении
            username_from_db = get_user(user_id)[2] if get_user(user_id) else "Неизвестный пользователь"
            await call.message.edit_caption(caption=f"✅ Платеж пользователя @{username_from_db} (ID: {user_id}) за {tariff.replace('_', ' ')} подтвержден. Конфиг отправлен.",
                                           reply_markup=None)
            await call.answer("Платеж подтвержден и конфиг отправлен пользователю.", show_alert=True)
        except Exception as e:
            logging.error(f"Не удалось отправить конфиг {config_path} пользователю {user_id}: {e}")
            username_from_db = get_user(user_id)[2] if get_user(user_id) else "Неизвестный пользователь"
            await call.message.edit_caption(caption=f"⚠️ Ошибка отправки конфига пользователю @{username_from_db} (ID: {user_id}). Платеж подтвержден, но конфиг не отправлен. Проверьте логи.",
                                           reply_markup=None)
            await call.answer("Произошла ошибка при отправке конфига.", show_alert=True)
    else:
        await call.answer("Этот платеж уже был обработан или не существует.", show_alert=True)
        # Если кнопки все еще есть, удаляем их
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
        await call.message.edit_caption(caption=f"❌ Платеж пользователя @{username_from_db} (ID: {user_id}) за {payment[3].replace('_', ' ')} отклонен.",
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
        # Проверяем формат даты, если это строка, парсим
        if isinstance(end_date_str, str):
            try:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
        else:
            end_date = end_date_str # Если уже datetime object

        remaining_days = (end_date - datetime.datetime.now()).days
        if remaining_days < 0:
            remaining_days = 0 # Не показываем отрицательные дни
        
        message_text = f"Ваш личный кабинет:\n\n" \
                       f"🗓 Активная подписка до: `{end_date.strftime('%d.%m.%Y %H:%M')}`\n" \
                       f"Осталось: `{remaining_days} дней`\n" \
                       f"Тариф: `{active_sub[4].replace('_', ' ')}`"
    else:
        message_text = "Ваш личный кабинет:\n\nУ вас пока нет активных подписок. Купите VPN!"

    await call.message.edit_text(message_text, parse_mode="Markdown", reply_markup=get_cabinet_keyboard())
    await call.answer()

@dp.callback_query_handler(text="get_my_config")
async def get_my_config(call: types.CallbackQuery):
    active_sub = get_active_subscription(call.from_user.id)
    if active_sub:
        config_path = active_sub[5]
        if config_path and os.path.exists(config_path):
            with open(config_path, 'rb') as f:
                await bot.send_document(call.from_user.id, f, caption="Ваш текущий VPN-конфиг:")
        else:
            await call.message.answer("К сожалению, ваш конфиг не найден. Пожалуйста, свяжитесь с поддержкой.")
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
            message_text += f"- Тариф: `{sub[4].replace('_', ' ')}`\n" \
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
                   "4. Используйте конфиг в приложении (например, V2RayNG, Shadowrocket) для подключения к VPN.\n\n" \
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
        # Проверяем, что username бота доступен
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
@dp.callback_query_handler(text="admin_check_payments", user_id=ADMIN_ID)
async def admin_check_payments(call: types.CallbackQuery):
    pending_payments = get_pending_payments()
    if not pending_payments:
        await call.message.edit_text("Нет новых платежей, ожидающих подтверждения.", reply_markup=get_admin_menu_keyboard())
        await call.answer()
        return

    for payment in pending_payments:
        # payment = (id, user_id, amount, tariff, screenshot_id, status, created_at, confirmed_by, confirmed_at, username)
        payment_id = payment[0]
        user_id = payment[1]
        amount = payment[2]
        tariff = payment[3]
        screenshot_id = payment[4]
        username = payment[9] if payment[9] else "N/A" # Имя пользователя из таблицы users

        await bot.send_photo(
            chat_id=call.from_user.id,
            photo=screenshot_id,
            caption=f"🔔 Новый платеж ожидает подтверждения!\n\n"
                    f"Пользователь: @{username} (ID: {user_id})\n"
                    f"Тариф: {tariff.replace('_', ' ')}\n"
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

# @dp.callback_query_handler(text="admin_stats", user_id=ADMIN_ID)
# async def admin_stats(call: types.CallbackQuery):
#     await call.message.answer("Функция статистики пока находится в разработке.")
#     await call.answer()


# --- ЗАПУСК БОТА ---
if __name__ == '__main__':
    init_db()
    # Создаем папку для конфигов, если ее нет
    if not os.path.exists(CONFIGS_FOLDER):
        os.makedirs(CONFIGS_FOLDER)
        print(f"Папка '{CONFIGS_FOLDER}' создана. Пожалуйста, добавьте ваши VPN-конфиги в эту папку.")
    
    executor.start_polling(dp, skip_updates=True)