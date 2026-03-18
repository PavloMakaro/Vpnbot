import telebot
from telebot import types
import json
import time
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import signal
import sys
import uuid
import math
import zipfile
from yookassa import Configuration, Payment

# === ТОКЕНЫ И КОНФИГУРАЦИЯ ===
TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY'
ADMIN_USERNAME = '@Gl1ch555'
ADMIN_ID = 8320218178  # ← Замените на ваш реальный ID!

# === ЮKASSA ===
YOOKASSA_SHOP_ID = "1172989"
YOOKASSA_SECRET_KEY = "live_abcZFyD5DDi8YoFafjPEJO_2TjWa5BCIWwWbSJvgrf4"
CURRENCY = "RUB"

# Настройка ЮKassa SDK
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

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
def create_yookassa_payment(amount: int, description: str, user_id: str, return_url: str = None):
    """Создание платежа через ЮKassa Умный платеж"""
    try:
        # Генерируем уникальный ID для платежа
        payment_id = str(uuid.uuid4())
        
        # Если return_url не указан, используем простую ссылку
        if not return_url:
            return_url = "https://t.me/vpni50_bot"  # Замените на ваш username
        
        # Создаем данные для чека 54-ФЗ
        receipt_data = get_provider_data(float(amount), description)
        
        # Создаем платеж
        payment = Payment.create({
            "amount": {
                "value": f"{amount}.00",
                "currency": CURRENCY
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": user_id,
                "payment_type": "balance_topup"
            },
            "receipt": {
                "customer": {
                    "email": users_db.get(user_id, {}).get('email', 'no-email@example.com')
                },
                "items": [
                    {
                        "description": description[:128],
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{amount:.2f}",
                            "currency": CURRENCY
                        },
                        "vat_code": 1  # для самозанятых
                    }
                ]
            }
        }, payment_id)
        
        return payment
    except Exception as e:
        print(f"Ошибка создания платежа ЮKassa: {e}")
        return None

def get_provider_data(amount_rub: float, description: str = "Пополнение баланса"):
    """Данные для чека 54-ФЗ (для совместимости со старым кодом)"""
    return {
        "receipt": {
            "items": [
                {
                    "description": description[:128],
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{amount_rub:.2f}",
                        "currency": CURRENCY
                    },
                    "vat_code": 1  # для самозанятых
                }
            ]
        }
    }

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
        types.InlineKeyboardButton("Управление конфигами пользователей", callback_data="admin_manage_user_configs"),
        types.InlineKeyboardButton("Статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton("Бэкап данных", callback_data="admin_backup"),
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

# --- Пагинация списка пользователей ---
def build_users_list_page(page: int, per_page: int = 20):
    """Формирует страницу списка всех пользователей с пагинацией."""
    all_items = list(users_db.items())
    total = len(all_items)
    total_pages = max(1, math.ceil(total / per_page))
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    items = all_items[start:end]

    lines = [f"Всего пользователей: {total} • Страница {page}/{total_pages}\n"]
    for uid, user_data in items:
        username = user_data.get('username', 'N/A')
        balance = user_data.get('balance', 0)
        days_left = get_subscription_days_left(uid)
        sub_status = f"подписка: {days_left} дн." if days_left > 0 else "нет подписки"
        lines.append(f"@{username} (ID: {uid}) — {balance} ₽, {sub_status}")

    text = "\n".join(lines)

    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    if page > 1:
        buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_all_users_page_{page-1}"))
    buttons.append(types.InlineKeyboardButton("🔄 Обновить", callback_data=f"admin_all_users_page_{page}"))
    if page < total_pages:
        buttons.append(types.InlineKeyboardButton("➡️ Далее", callback_data=f"admin_all_users_page_{page+1}"))

    if buttons:
        kb.add(*buttons)
    kb.add(types.InlineKeyboardButton("🏠 Админ-панель", callback_data="admin_manage_users"))

    return text, kb

def build_admin_stats() -> str:
    """Собирает ключевые метрики для админской статистики."""
    try:
        now = datetime.datetime.now()
        total_users = len(users_db)
        with_subscription = 0
        active_users = 0
        total_balance = 0

        for uid, u in users_db.items():
            total_balance += float(u.get('balance', 0) or 0)
            sub_end = u.get('subscription_end')
            if sub_end:
                with_subscription += 1
                try:
                    end_dt = datetime.datetime.strptime(sub_end, '%Y-%m-%d %H:%M:%S')
                    if end_dt > now:
                        active_users += 1
                except Exception:
                    pass

        total_payments = len(payments_db)
        pending_payments = 0
        confirmed_payments = 0
        rejected_payments = 0
        total_revenue = 0.0
        for p in payments_db.values():
            status = p.get('status')
            amount = float(p.get('amount', 0) or 0)
            if status == 'pending':
                pending_payments += 1
            elif status == 'confirmed':
                confirmed_payments += 1
                total_revenue += amount
            elif status == 'rejected':
                rejected_payments += 1

        lines = []
        lines.append("Статистика системы:")
        lines.append(f"Пользователи: {total_users}")
        lines.append(f"С подпиской: {with_subscription} • Активных: {active_users}")
        lines.append(f"Суммарный баланс пользователей: {int(total_balance)} ₽")
        lines.append("")
        lines.append("Платежи ЮKassa:")
        lines.append(f"Всего: {total_payments} • Подтверждено: {confirmed_payments} • Отклонено: {rejected_payments} • В ожидании: {pending_payments}")
        lines.append(f"Подтвержденная выручка: {int(total_revenue)} ₽")
        lines.append("")
        lines.append("Конфиги по периодам:")
        for period_key, period_info in SUBSCRIPTION_PERIODS.items():
            period_days = period_info.get('days', period_key)
            configs_list = configs_db.get(period_key, [])
            total_cfg = len(configs_list)
            available_cfg = sum(1 for c in configs_list if not c.get('used', False))
            used_cfg = total_cfg - available_cfg
            lines.append(f"{period_days} дней: всего {total_cfg}, доступно {available_cfg}, выдано {used_cfg}")

        return "\n".join(lines)
    except Exception as e:
        return f"Не удалось собрать статистику: {e}"

# --- Создание бэкапа данных ---
def create_backup_zip():
    """Создаёт zip-бэкап файлов данных и возвращает путь к архиву."""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backups_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        if not os.path.exists(backups_dir):
            os.makedirs(backups_dir)
        backup_path = os.path.join(backups_dir, f'backup_{timestamp}.zip')

        files_to_backup = []
        for fname in ['users.json', 'configs.json', 'payments.json']:
            fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
            try:
                os.stat(fpath)
                files_to_backup.append(fpath)
            except OSError:
                pass

        # Если данных нет, всё равно создаём пустой архив для последовательности
        with zipfile.ZipFile(backup_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for f in files_to_backup:
                zf.write(f, arcname=os.path.basename(f))

        return backup_path
    except Exception as e:
        print(f"Ошибка создания бэкапа: {e}")
        return None

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
    markup.add(types.InlineKeyboardButton("💳 Пополнить баланс", callback_data="topup_balance"))
    markup.add(types.InlineKeyboardButton("📦 Купить подписку с баланса", callback_data="buy_subscription"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
    return markup

def topup_balance_keyboard():
    """Клавиатура для пополнения баланса"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    amounts = [100, 200, 500, 1000, 2000, 5000]
    for amount in amounts:
        markup.add(types.InlineKeyboardButton(f"{amount} ₽", callback_data=f"topup_{amount}"))
    markup.add(types.InlineKeyboardButton("💰 Ввести свою сумму", callback_data="topup_custom"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="buy_vpn"))
    return markup

def buy_subscription_keyboard():
    """Клавиатура для покупки подписки с баланса"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for period_key, period_data in SUBSCRIPTION_PERIODS.items():
        markup.add(types.InlineKeyboardButton(f"{period_data['days']} дней ({period_data['price']} ₽)", callback_data=f"buy_sub_{period_key}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="buy_vpn"))
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
    """Упрощённая клавиатура для раздела 'Мои конфиги' — без выбора периода."""
    markup = types.InlineKeyboardMarkup(row_width=1)
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

# --- Повторная выдача ранее полученного конфига ---
def get_last_config_for_period(user_id, period):
    """Возвращает последний выданный конфиг пользователя для указанного периода (если есть)."""
    user_info = users_db.get(str(user_id), {})
    used_configs = user_info.get('used_configs', [])
    for conf in reversed(used_configs):
        if conf.get('period') == period:
            return conf
    return None

# === Инструкции по использованию VPN ===
def build_usage_instructions(config_link: str, config_code: str = None) -> str:
    """Возвращает текстовые инструкции по использованию VPN на популярных платформах.
    config_link — ссылка или импорт-URL вашего конфига.
    config_code — код/строка конфигурации (если приложение требует)."""
    code_line = f"\n🔑 Код (если требуется): `{config_code}`" if config_code else ""
    return (
        "📘 **Инструкции по использованию VPN**\n\n"
        "🔗 **Ваша ссылка на конфиг:**\n"
        f"`{config_link}`{code_line}\n\n"
        "🪟 **Windows (Clash Verge / v2rayN / OpenVPN)**\n"
        "- Установите приложение, поддерживающее импорт ссылки или файла.\n"
        "- Откройте приложение и выберите импорт по URL/Clipboard.\n"
        "- Вставьте ссылку выше и примените профиль.\n"
        "- Подключитесь к выбранному серверу.\n\n"
        "📱 **Android (v2rayNG / OpenVPN)**\n"
        "- Установите v2rayNG или OpenVPN из Google Play.\n"
        "- Нажмите + и выберите импорт из буфера обмена/URL.\n"
        "- Вставьте ссылку и сохраните профиль.\n"
        "- Нажмите старт для подключения.\n\n"
        "🍎 **iOS (Shadowrocket / Quantumult X)**\n"
        "- Установите приложение из App Store (требуется платное).\n"
        "- Добавьте конфигурацию по URL, вставьте ссылку.\n"
        "- Разрешите создание VPN-профиля и подключитесь.\n\n"
        "🍏 **macOS (ClashX / Tunnelblick)**\n"
        "- Установите ClashX или Tunnelblick.\n"
        "- Импортируйте конфигурацию через URL/файл.\n"
        "- Активируйте профиль и подключитесь.\n\n"
        "🐧 **Linux (OpenVPN / NetworkManager)**\n"
        "- Установите `openvpn` или используйте NetworkManager.\n"
        "- Импорт по файлу или URL (в зависимости от приложения).\n"
        "- Запустите подключение и проверьте, что трафик идёт через VPN.\n\n"
        "ℹ️ Если у вас возникли сложности — напишите в поддержку "
        f"{ADMIN_USERNAME}."
    )

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
        
        welcome_text = f"🎉 **Добро пожаловать в VPN Bot!**\n\n"
        welcome_text += f"👤 **Имя:** {first_name}\n"
        welcome_text += f"📱 **Username:** @{username}\n"
        welcome_text += f"💰 **Баланс:** {REFERRAL_BONUS_NEW_USER} ₽ (приветственный бонус)\n"
        welcome_text += f"📅 **Подписка:** Нет активной подписки\n"
        if referred_by_id:
            welcome_text += f"🤝 **Реферал:** Зарегистрировались по реферальной ссылке!\n"
        welcome_text += f"\n🚀 **Начните с пополнения баланса и покупки подписки!**"
        
        bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=main_menu_keyboard(message.from_user.id))
    else:
        # Пользователь уже существует - показываем его данные
        user_info = users_db[user_id]
        balance = user_info.get('balance', 0)
        subscription_end = user_info.get('subscription_end')
        days_left = get_subscription_days_left(user_id)
        referrals_count = user_info.get('referrals_count', 0)
        
        status_text = "❌ Нет активной подписки"
        if days_left > 0:
            end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
            status_text = f"✅ Активна еще {days_left} дней (до {end_date.strftime('%d.%m.%Y')})"
        
        welcome_text = f"👋 **С возвращением, {first_name}!**\n\n"
        welcome_text += f"👤 **Имя:** {first_name}\n"
        welcome_text += f"📱 **Username:** @{username}\n"
        welcome_text += f"💰 **Баланс:** {balance} ₽\n"
        welcome_text += f"📅 **Подписка:** {status_text}\n"
        welcome_text += f"🤝 **Рефералов:** {referrals_count}\n"
        welcome_text += f"\n🚀 **Что хотите сделать?**"
        
        bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=main_menu_keyboard(message.from_user.id))

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
    elif call.data == "buy_vpn":
        bot.edit_message_text("💳 **Пополнение и покупка VPN**\n\n"
                              "1️⃣ **Пополните баланс** - выберите сумму для пополнения\n"
                              "2️⃣ **Купите подписку** - используйте средства с баланса\n\n"
                              "💰 Ваш текущий баланс будет показан при покупке подписки",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown', reply_markup=buy_vpn_keyboard())
    
    elif call.data == "topup_balance":
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        bot.edit_message_text(f"💳 **Пополнение баланса**\n\n"
                              f"💰 Текущий баланс: {user_balance} ₽\n\n"
                              f"Выберите сумму для пополнения:",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown', reply_markup=topup_balance_keyboard())
    
    elif call.data == "buy_subscription":
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        bot.edit_message_text(f"📦 **Покупка подписки с баланса**\n\n"
                              f"💰 Ваш баланс: {user_balance} ₽\n\n"
                              f"Выберите период подписки:",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown', reply_markup=buy_subscription_keyboard())
    elif call.data.startswith("topup_") and call.data != "topup_custom":
        amount = int(call.data.replace("topup_", ""))
        
        # Создаем платеж через ЮKassa
        payment = create_yookassa_payment(
            amount=amount,
            description=f"Пополнение баланса на {amount} ₽",
            user_id=user_id
        )
        
        if payment and payment.confirmation:
            # Отправляем ссылку на оплату
            bot.send_message(
                call.message.chat.id,
                f"💳 **Пополнение баланса на {amount} ₽**\n\n"
                f"🔗 [Перейти к оплате]({payment.confirmation.confirmation_url})\n\n"
                f"После оплаты баланс будет автоматически пополнен.\n"
                f"Поддерживаются все способы оплаты: карты, СБП, ЮMoney и другие.",
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("💳 Оплатить", url=payment.confirmation.confirmation_url)
                ).add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="topup_balance")
                )
            )
            
            # Сохраняем информацию о платеже
            payments_db[payment.id] = {
                'user_id': user_id,
                'amount': amount,
                'status': 'pending',
                'method': 'yookassa_smart',
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'balance_topup',
                'payment_id': payment.id
            }
            save_data('payments.json', payments_db)
            
        else:
            bot.send_message(
                call.message.chat.id,
                "❌ Ошибка создания платежа. Попробуйте позже или обратитесь в поддержку.",
                reply_markup=topup_balance_keyboard()
            )
        
        bot.answer_callback_query(call.id)
    
    elif call.data == "topup_custom":
        bot.edit_message_text("💰 **Введите сумму для пополнения баланса**\n\n"
                              "Минимальная сумма: 50 ₽\n"
                              "Максимальная сумма: 50,000 ₽\n\n"
                              "Введите только число (например: 1500)",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown')
        bot.register_next_step_handler(call.message, process_custom_topup)
    
    elif call.data.startswith("buy_sub_"):
        period_data_key = call.data.replace("buy_sub_", "")
        amount = SUBSCRIPTION_PERIODS[period_data_key]['price']
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        days_left = get_subscription_days_left(user_id)
        
        if user_balance < amount:
            needed_amount = amount - user_balance
            bot.edit_message_text(f"❌ **Недостаточно средств на балансе!**\n\n"
                                  f"💰 Ваш баланс: {user_balance} ₽\n"
                                  f"💳 Требуется: {amount} ₽\n"
                                  f"💸 Не хватает: {needed_amount} ₽\n\n"
                                  f"Пожалуйста, сначала пополните баланс.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown', reply_markup=buy_vpn_keyboard())
            return
        
        # Покупка с баланса
        users_db[user_id]['balance'] = user_balance - amount
        current_end = users_db[user_id].get('subscription_end')
        if current_end:
            current_end = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
        else:
            current_end = datetime.datetime.now()
        add_days = SUBSCRIPTION_PERIODS[period_data_key]['days']
        new_end = current_end + datetime.timedelta(days=add_days)
        users_db[user_id]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
        save_data('users.json', users_db)
    
        success, result = send_config_to_user(user_id, period_data_key,
                                        users_db[user_id].get('username', 'user'),
                                        users_db[user_id].get('first_name', 'User'))
    
        if success:
            bot.edit_message_text(f"✅ **Подписка успешно куплена!**\n\n"
                                      f"💳 Списано с баланса: {amount} ₽\n"
                                      f"💰 Остаток на балансе: {users_db[user_id]['balance']} ₽\n"
                                      f"📅 Подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                      f"🔐 Конфиг уже выдан! Проверьте сообщения выше.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown', reply_markup=main_menu_keyboard(user_id))
            # Дополнительно отправляем инструкции по использованию VPN
            try:
                instructions = build_usage_instructions(result.get('link'), result.get('code'))
                bot.send_message(int(user_id), instructions, parse_mode='Markdown')
            except Exception as e:
                print(f"Не удалось отправить инструкции пользователю {user_id}: {e}")
        else:
            bot.edit_message_text(f"✅ **Подписка куплена, но возникла ошибка при выдаче конфига:**\n\n"
                                  f"❌ {result}\n\n"
                                      f"Обратитесь в поддержку: {ADMIN_USERNAME}",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown', reply_markup=main_menu_keyboard(user_id))

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
        # Выводим список всех ранее выданных конфигов пользователю
        uinfo = users_db.get(str(user_id), {})
        used_configs = uinfo.get('used_configs', [])
        if not used_configs:
            text = "📦 У вас пока нет выданных конфигов.\n\n" \
                   "После покупки подписки конфиг будет выдан автоматически."
        else:
            lines = ["🔐 Ваши выданные конфиги:\n"]
            for idx, conf in enumerate(used_configs, start=1):
                period_days = SUBSCRIPTION_PERIODS.get(conf.get('period'), {}).get('days', conf.get('period'))
                lines.append(
                    f"{idx}. {conf.get('config_name','Конфиг')}\n"
                    f"   • Период: {period_days} дней\n"
                    f"   • Дата выдачи: {conf.get('issue_date')}\n"
                    f"   • Ссылка: {conf.get('config_link')}\n"
                )
            text = "\n".join(lines)
        bot.edit_message_text(text,
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=my_configs_keyboard(user_id))
    elif call.data.startswith("get_config_"):
        period_data_key = call.data.replace("get_config_", "")
        user_info = users_db.get(user_id, {})
        days_left = get_subscription_days_left(user_id)
        if days_left <= 0:
            bot.answer_callback_query(call.id, "❌ У вас нет активной подписки или подписка истекла.", show_alert=True)
            bot.edit_message_text("Выберите конфиг для получения (если у вас активна подписка):\n"
                              "❕_В профиле будет прислан тот же конфиг, что и при покупке. Если ранее конфиг не выдавался — вы получите новый._",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown',
                              reply_markup=my_configs_keyboard(user_id))
            return
        # Сначала пробуем выдать ранее полученный конфиг для этого периода
        existing = get_last_config_for_period(user_id, period_data_key)
        if existing:
            try:
                bot.send_message(int(user_id),
                                 f"🔐 **Ваш VPN конфиг**\n"
                                 f"🗂️ **Описание:** {existing.get('config_name', 'Конфиг')}\n"
                                 f"📅 **Период:** {SUBSCRIPTION_PERIODS[period_data_key]['days']} дней\n"
                                 f"🔗 **Ссылка на конфиг:** {existing.get('config_link')}\n"
                                 f"💾 _Сохраните этот конфиг для использования_",
                                 parse_mode='Markdown')
                bot.answer_callback_query(call.id, "✅ Ранее выданный конфиг отправлен!", show_alert=True)
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ Ошибка отправки: {e}", show_alert=True)
        else:
            # Если ранее конфиг не выдавался, выдаем новый
            success, result = send_config_to_user(user_id, period_data_key,
                                                 user_info.get('username', 'user'),
                                                 user_info.get('first_name', 'User'))
            if success:
                bot.answer_callback_query(call.id, "✅ Конфиг успешно выдан! Проверьте сообщения.", show_alert=True)
            else:
                bot.answer_callback_query(call.id, f"❌ {result}", show_alert=True)
    elif call.data == "support":
        bot.edit_message_text(f"Для связи с поддержкой напишите {ADMIN_USERNAME}.\n"
                              f"Постараемся ответить как можно скорее.",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=main_menu_keyboard(user_id))
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
    elif call.data == "admin_manage_configs":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Управление конфигами:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=manage_configs_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    elif call.data == "admin_stats":
        if str(user_id) == str(ADMIN_ID):
            stats_text = build_admin_stats()
            bot.edit_message_text(stats_text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    elif call.data == "admin_show_configs":
        if str(user_id) == str(ADMIN_ID):
            message_text = "**Текущие конфиги:**\n"
            for period, configs_list in configs_db.items():
                message_text += f"**{SUBSCRIPTION_PERIODS.get(period, {}).get('days', period)} дней:**\n"
                if configs_list:
                    available_count = sum(1 for config in configs_list if not config.get('used', False))
                    message_text += f"  Всего: {len(configs_list)}, Доступно: {available_count}\n"
                    for i, config in enumerate(configs_list):
                        status = "✅" if not config.get('used', False) else "❌"
                        message_text += f"  {i+1}. {status} {config['name']} - `{config['link']}`\n"
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
            bot.edit_message_text(f"Добавление конфигов для периода: {SUBSCRIPTION_PERIODS[period]['days']} дней\n"
                                 f"Отправьте ссылки на конфиги, каждую с новой строки.\n"
                                 f"Имена будут сгенерированы автоматически на основе username администратора и номера конфига.",
                                 chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_add_configs_bulk, period)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    elif call.data == "admin_delete_config":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Введите период и ID конфига для удаления (например, `1_month 1` для первого конфига на 30 дней, ID начинаются с 1).",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  parse_mode='Markdown', reply_markup=manage_configs_keyboard())
            bot.register_next_step_handler(call.message, process_delete_config)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    elif call.data == "admin_confirm_payments":
        if str(user_id) == str(ADMIN_ID):
            pending_payments = {pid: p_data for pid, p_data in payments_db.items() if p_data['status'] == 'pending' and p_data.get('screenshot_id')}
            if not pending_payments:
                bot.edit_message_text("Нет платежей, ожидающих подтверждения со скриншотами.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_keyboard())
                return
            for payment_id, p_data in pending_payments.items():
                user_payment_info = users_db.get(p_data['user_id'])
                username_str = user_payment_info.get('username', 'N/A') if user_payment_info else 'N/A'
                bot.send_photo(ADMIN_ID, p_data['screenshot_id'],
                               caption=f"Платеж ID: `{payment_id}`\n"
                                       f"От: @{username_str} (ID: {p_data['user_id']})\n"
                                       f"Сумма: {p_data['amount']} ₽\n"
                                       f"Период: {SUBSCRIPTION_PERIODS.get(p_data['period'], {}).get('days', p_data['period'])} дней\n"
                                       f"Время: {p_data['timestamp']}",
                               parse_mode='Markdown', reply_markup=confirm_payments_keyboard(payment_id))
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
                                         f"Конфиг уже выдан! Проверьте сообщения выше.",
                                         reply_markup=main_menu_keyboard(target_user_id))
                        # Отправляем инструкции по использованию VPN после подтверждения админом
                        try:
                            instructions = build_usage_instructions(result.get('link'), result.get('code'))
                            bot.send_message(int(target_user_id), instructions, parse_mode='Markdown')
                        except Exception as e:
                            print(f"Не удалось отправить инструкции пользователю {target_user_id}: {e}")
                    else:
                        bot.send_message(target_user_id,
                                         f"✅ Платеж подтвержден, но возникла ошибка при выдаче конфига: {result}\n"
                                         f"Обратитесь в поддержку: {ADMIN_USERNAME}",
                                         reply_markup=main_menu_keyboard(target_user_id))
                save_data('payments.json', payments_db)
                bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                         caption=f"{call.message.caption}\n✅ Подтвержден администратором.",
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
                                         caption=f"{call.message.caption}\n❌ Отклонен администратором.",
                                         reply_markup=None, parse_mode='Markdown')
            else:
                bot.answer_callback_query(call.id, "Платеж уже обработан или не найден.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    # --- Управление пользователями и конфигами (остальное без изменений) ---
    # [Сюда вставляются все остальные elif из оригинального файла: admin_manage_users, admin_active_users и т.д.]
    # → Для краткости и из-за ограничения длины ответа, я опускаю их — они **остаются без изменений**.
    # Весь код ниже (админка, рассылка, редактирование и т.п.) остаётся как в оригинале.
    # Единственное: удалите обработчики, связанные с pay_card и pay_stars, если они ещё остались.

    # Пример: перенаправление на админку
    elif call.data == "admin_manage_users":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Управление пользователями:",
                                 chat_id=call.message.chat.id, message_id=call.message.message_id,
                                 reply_markup=users_management_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    # --- Дополнительные админские обработчики ---
    elif call.data == "admin_active_users":
        if str(user_id) == str(ADMIN_ID):
            active_users = []
            for uid, user_data in users_db.items():
                if user_data.get('subscription_end'):
                    end_date = datetime.datetime.strptime(user_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                    if end_date > datetime.datetime.now():
                        active_users.append(f"@{user_data.get('username', 'N/A')} (ID: {uid})")
            
            message_text = f"**Активные пользователи ({len(active_users)}):**\n"
            if active_users:
                message_text += "\n".join(active_users[:20])  # Ограничиваем вывод
                if len(active_users) > 20:
                    message_text += f"\n... и еще {len(active_users) - 20} пользователей"
            else:
                message_text += "Нет активных пользователей"
            
            bot.edit_message_text(message_text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                parse_mode='Markdown', reply_markup=users_management_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_all_users":
        if str(user_id) == str(ADMIN_ID):
            # Переходим на первую страницу списка всех пользователей
            page = 1
            text, kb = build_users_list_page(page)
            bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=kb)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

    elif call.data.startswith("admin_all_users_page_"):
        if str(user_id) == str(ADMIN_ID):
            try:
                page = int(call.data.replace("admin_all_users_page_", ""))
            except ValueError:
                page = 1
            text, kb = build_users_list_page(page)
            bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=kb)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_search_user":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Введите ID пользователя или username для поиска:",
                                chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_search_user)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_edit_user_start":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Введите ID пользователя для редактирования:",
                                chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_edit_user_start)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_show_user_configs":
        if str(user_id) == str(ADMIN_ID):
            message_text = "**Выданные конфиги:**\n"
            total_configs = 0
            for uid, user_data in users_db.items():
                used_configs = user_data.get('used_configs', [])
                if used_configs:
                    username = user_data.get('username', 'N/A')
                    message_text += f"**@{username} (ID: {uid}):**\n"
                    for config in used_configs:
                        message_text += f"  • {config['config_name']} ({config['period']}) - {config['issue_date']}\n"
                        total_configs += 1
                    message_text += "\n"
            
            if total_configs == 0:
                message_text += "Нет выданных конфигов"
            else:
                message_text = f"**Всего выданных конфигов: {total_configs}**\n\n" + message_text
            
            bot.edit_message_text(message_text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                parse_mode='Markdown', reply_markup=user_configs_management_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_broadcast":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("Введите сообщение для рассылки:",
                                chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_broadcast)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data == "admin_backup":
        if str(user_id) == str(ADMIN_ID):
            backup_path = create_backup_zip()
            if backup_path and os.path.exists(backup_path):
                try:
                    with open(backup_path, 'rb') as f:
                        bot.send_document(ADMIN_ID, f, caption=f"✅ Бэкап создан: {os.path.basename(backup_path)}")
                    bot.edit_message_text("✅ Бэкап данных успешно создан и отправлен.",
                                          chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=admin_keyboard())
                except Exception as e:
                    bot.edit_message_text(f"❌ Ошибка отправки бэкапа: {e}\nФайл: {backup_path}",
                                          chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=admin_keyboard())
            else:
                bot.edit_message_text("❌ Не удалось создать бэкап.",
                                      chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    # Обработчики для редактирования пользователей
    elif call.data.startswith("admin_edit_balance_"):
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_edit_balance_", "")
            bot.edit_message_text(f"Введите новую сумму баланса для пользователя {target_user_id}:",
                                chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_edit_balance, target_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data.startswith("admin_edit_subscription_"):
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_edit_subscription_", "")
            bot.edit_message_text(f"Введите новую дату окончания подписки для пользователя {target_user_id} (формат: YYYY-MM-DD HH:MM:SS):",
                                chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.register_next_step_handler(call.message, process_edit_subscription, target_user_id)
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")
    
    elif call.data.startswith("admin_view_user_configs_"):
        if str(user_id) == str(ADMIN_ID):
            target_user_id = call.data.replace("admin_view_user_configs_", "")
            user_data = users_db.get(target_user_id, {})
            used_configs = user_data.get('used_configs', [])
            
            if used_configs:
                message_text = f"**Конфиги пользователя @{user_data.get('username', 'N/A')}:**\n\n"
                for i, config in enumerate(used_configs, 1):
                    message_text += f"{i}. **{config['config_name']}**\n"
                    message_text += f"   Период: {config['period']}\n"
                    message_text += f"   Дата выдачи: {config['issue_date']}\n"
                    message_text += f"   Ссылка: `{config['config_link']}`\n\n"
            else:
                message_text = f"У пользователя @{user_data.get('username', 'N/A')} нет выданных конфигов."
            
            bot.edit_message_text(message_text, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                parse_mode='Markdown', reply_markup=user_action_keyboard(target_user_id))
        else:
            bot.answer_callback_query(call.id, "У вас нет прав администратора.")

# === ОБРАБОТЧИКИ ПЛАТЕЖЕЙ (удалены - теперь используется ЮKassa Умный платеж) ===

# === АДМИНСКИЕ ОБРАБОТЧИКИ ===
def process_add_configs_bulk(message, period):
    """Обработка добавления конфигов пачкой"""
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    config_links = message.text.strip().split('\n')
    added_count = 0
    
    if period not in configs_db:
        configs_db[period] = []
    
    for i, link in enumerate(config_links, 1):
        if link.strip():
            config_name = f"Config_{period}_{len(configs_db[period]) + 1}"
            configs_db[period].append({
                'name': config_name,
                'link': link.strip(),
                'code': f"code_{period}_{len(configs_db[period])}",
                'used': False
            })
            added_count += 1
    
    save_data('configs.json', configs_db)
    bot.send_message(message.chat.id, f"✅ Добавлено {added_count} конфигов для периода {SUBSCRIPTION_PERIODS[period]['days']} дней.",
                    reply_markup=manage_configs_keyboard())

def process_delete_config(message):
    """Обработка удаления конфига"""
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: `период ID` (например: 1_month 1)",
                           parse_mode='Markdown', reply_markup=manage_configs_keyboard())
            return
        
        period, config_id = parts[0], int(parts[1]) - 1  # ID начинается с 1
        
        if period not in configs_db or config_id < 0 or config_id >= len(configs_db[period]):
            bot.send_message(message.chat.id, "❌ Конфиг не найден.", reply_markup=manage_configs_keyboard())
            return
        
        deleted_config = configs_db[period].pop(config_id)
        save_data('configs.json', configs_db)
        bot.send_message(message.chat.id, f"✅ Удален конфиг: {deleted_config['name']}",
                        reply_markup=manage_configs_keyboard())
    
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "❌ Ошибка в формате данных.", reply_markup=manage_configs_keyboard())

def process_search_user(message):
    """Поиск пользователя"""
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    search_term = message.text.strip()
    found_users = []
    
    for uid, user_data in users_db.items():
        if (search_term.lower() in str(uid).lower() or 
            search_term.lower() in user_data.get('username', '').lower()):
            found_users.append((uid, user_data))
    
    if found_users:
        message_text = f"**Найдено пользователей: {len(found_users)}**\n\n"
        for uid, user_data in found_users[:5]:  # Показываем первых 5
            username = user_data.get('username', 'N/A')
            balance = user_data.get('balance', 0)
            message_text += f"@{username} (ID: {uid}) - {balance} ₽\n"
        
        if len(found_users) > 5:
            message_text += f"... и еще {len(found_users) - 5} пользователей"
        
        bot.send_message(message.chat.id, message_text, parse_mode='Markdown',
                        reply_markup=users_management_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Пользователи не найдены.",
                        reply_markup=users_management_keyboard())

def process_edit_user_start(message):
    """Начало редактирования пользователя"""
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    target_user_id = message.text.strip()
    if target_user_id not in users_db:
        bot.send_message(message.chat.id, "❌ Пользователь не найден.",
                        reply_markup=users_management_keyboard())
        return
    
    user_data = users_db[target_user_id]
    bot.send_message(message.chat.id, 
                    f"**Пользователь:** @{user_data.get('username', 'N/A')} (ID: {target_user_id})\n"
                    f"**Баланс:** {user_data.get('balance', 0)} ₽\n"
                    f"**Подписка до:** {user_data.get('subscription_end', 'Нет')}\n\n"
                    f"Выберите действие:",
                    parse_mode='Markdown',
                    reply_markup=user_action_keyboard(target_user_id))

def process_broadcast(message):
    """Рассылка сообщений"""
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    broadcast_text = message.text
    sent_count = 0
    failed_count = 0
    
    for user_id in users_db.keys():
        try:
            bot.send_message(int(user_id), broadcast_text)
            sent_count += 1
        except Exception as e:
            failed_count += 1
            print(f"Ошибка отправки пользователю {user_id}: {e}")
    
    bot.send_message(message.chat.id, 
                    f"✅ Рассылка завершена!\n"
                    f"Отправлено: {sent_count}\n"
                    f"Ошибок: {failed_count}",
                    reply_markup=admin_keyboard())

def process_edit_balance(message, target_user_id):
    """Редактирование баланса пользователя"""
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    try:
        new_balance = float(message.text.strip())
        if target_user_id in users_db:
            users_db[target_user_id]['balance'] = new_balance
            save_data('users.json', users_db)
            bot.send_message(message.chat.id, 
                           f"✅ Баланс пользователя {target_user_id} изменен на {new_balance} ₽",
                           reply_markup=users_management_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.",
                           reply_markup=users_management_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат суммы.",
                        reply_markup=users_management_keyboard())

def process_edit_subscription(message, target_user_id):
    """Редактирование подписки пользователя"""
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    
    try:
        new_date = message.text.strip()
        # Проверяем формат даты
        datetime.datetime.strptime(new_date, '%Y-%m-%d %H:%M:%S')
        
        if target_user_id in users_db:
            users_db[target_user_id]['subscription_end'] = new_date
            save_data('users.json', users_db)
            bot.send_message(message.chat.id, 
                           f"✅ Подписка пользователя {target_user_id} изменена до {new_date}",
                           reply_markup=users_management_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.",
                           reply_markup=users_management_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат даты. Используйте: YYYY-MM-DD HH:MM:SS",
                        reply_markup=users_management_keyboard())

def process_custom_topup(message):
    """Обработка ввода произвольной суммы для пополнения"""
    try:
        amount = int(message.text.strip())
        
        if amount < 50:
            bot.send_message(message.chat.id, "❌ Минимальная сумма пополнения: 50 ₽",
                           reply_markup=topup_balance_keyboard())
            return
        
        if amount > 50000:
            bot.send_message(message.chat.id, "❌ Максимальная сумма пополнения: 50,000 ₽",
                           reply_markup=topup_balance_keyboard())
            return
        
        # Создаем платеж через ЮKassa
        payment = create_yookassa_payment(
            amount=amount,
            description=f"Пополнение баланса на {amount} ₽",
            user_id=str(message.from_user.id)
        )
        
        if payment and payment.confirmation:
            # Отправляем ссылку на оплату
            bot.send_message(
                message.chat.id,
                f"💳 **Пополнение баланса на {amount} ₽**\n\n"
                f"🔗 [Перейти к оплате]({payment.confirmation.confirmation_url})\n\n"
                f"После оплаты баланс будет автоматически пополнен.\n"
                f"Поддерживаются все способы оплаты: карты, СБП, ЮMoney и другие.",
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("💳 Оплатить", url=payment.confirmation.confirmation_url)
                ).add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="topup_balance")
                )
            )
            
            # Сохраняем информацию о платеже
            payments_db[payment.id] = {
                'user_id': str(message.from_user.id),
        'amount': amount,
                'status': 'pending',
                'method': 'yookassa_smart',
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'balance_topup',
                'payment_id': payment.id
            }
            save_data('payments.json', payments_db)

        else:
            bot.send_message(
                message.chat.id,
                "❌ Ошибка создания платежа. Попробуйте позже или обратитесь в поддержку.",
                reply_markup=topup_balance_keyboard()
            )
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректную сумму (только число)",
                        reply_markup=topup_balance_keyboard())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}",
                        reply_markup=topup_balance_keyboard())

# === ПРОВЕРКА СТАТУСА ПЛАТЕЖЕЙ ===
def _check_single_payment(payment_id, payment_data):
    try:
        payment = Payment.find_one(payment_id)
        return payment_id, payment_data, payment.status
    except Exception as e:
        print(f"Ошибка проверки платежа {payment_id}: {e}")
        return payment_id, payment_data, None

def check_pending_payments():
    """Проверка статуса ожидающих платежей"""
    try:
        pending_payments = [(pid, pdata) for pid, pdata in payments_db.items()
                            if pdata.get('status') == 'pending' and pdata.get('method') == 'yookassa_smart']
        if not pending_payments:
            return

        users_modified = False
        payments_modified = False

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_check_single_payment, pid, pdata) for pid, pdata in pending_payments]

            for future in futures:
                payment_id, payment_data, status = future.result()
                if not status:
                    continue
                    
                if status == 'succeeded':
                    user_id = payment_data['user_id']
                    if user_id not in users_db:
                        print(f"User {user_id} not found in users_db for payment {payment_id}")
                        continue
                        
                    amount = payment_data['amount']
                    current_balance = users_db[user_id].get('balance', 0)
                    users_db[user_id]['balance'] = current_balance + amount
                    users_modified = True

                    payments_db[payment_id]['status'] = 'confirmed'
                    payments_modified = True

                    try:
                        bot.send_message(
                            user_id,
                            f"✅ **Баланс успешно пополнен!**\n\n"
                            f"💰 Пополнено: {amount} ₽\n"
                            f"💳 Новый баланс: {users_db[user_id]['balance']} ₽\n\n"
                            f"Теперь вы можете купить подписку!",
                            parse_mode='Markdown',
                            reply_markup=main_menu_keyboard(user_id)
                        )
                        bot.send_message(
                            ADMIN_ID,
                            f"✅ Пополнение баланса через ЮKassa:\n"
                            f"Пользователь: @{users_db[user_id].get('username', 'N/A')} (ID: {user_id})\n"
                            f"Сумма: {amount} ₽"
                        )
                    except Exception as e:
                        print(f"Error sending messages: {e}")
                        
                elif status == 'canceled':
                    payments_db[payment_id]['status'] = 'canceled'
                    payments_modified = True
                    try:
                        bot.send_message(
                            payment_data['user_id'],
                            f"❌ Платеж отменен. Баланс не пополнен.",
                            reply_markup=main_menu_keyboard(payment_data['user_id'])
                        )
                    except Exception as e:
                        print(f"Error sending message: {e}")
                        
        if users_modified:
            save_data('users.json', users_db)
        if payments_modified:
            save_data('payments.json', payments_db)

    except Exception as e:
        print(f"Ошибка проверки платежей: {e}")

# === ПЕРИОДИЧЕСКАЯ ПРОВЕРКА ПЛАТЕЖЕЙ ===
def payment_checker():
    """Периодическая проверка статуса платежей"""
    while True:
        try:
            check_pending_payments()
            time.sleep(30)  # Проверяем каждые 30 секунд
        except Exception as e:
            print(f"Ошибка в payment_checker: {e}")
            time.sleep(60)

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
    
    # Запускаем проверку платежей в отдельном потоке
    payment_thread = threading.Thread(target=payment_checker, daemon=True)
    payment_thread.start()
    print("✅ Проверка платежей ЮKassa запущена")
    
    # Запускаем бота
    bot.polling(none_stop=True, interval=0, timeout=60)
