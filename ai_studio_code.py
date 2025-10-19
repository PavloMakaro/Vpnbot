import telebot
from telebot import types
import json
import time
import datetime
import threading

TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY'
ADMIN_USERNAME = '@Gl1ch555'
ADMIN_ID = 8320218178
CARD_NUMBER = '2204320690808227'
CARD_HOLDER = 'Makarov Pavel Alexandrovich (Ozon Bank)'

PRICE_MONTH = 50
PRICE_2_MONTHS = 90
PRICE_3_MONTHS = 120

REFERRAL_BONUS_NEW_USER = 50
REFERRAL_BONUS_RUB = 25
REFERRAL_BONUS_DAYS = 7

bot = telebot.TeleBot(TOKEN)

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

# УДАЛЯЕМ ВСЕ КОНФИГИ ПРИ СТАРТЕ БОТА, КАК ВЫ ПРОСИЛИ
configs_db = {'1_month': [], '2_months': [], '3_months': []}
save_data('configs.json', configs_db)

def generate_payment_id():
    return str(int(time.time() * 100000))

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

def payment_methods_keyboard(period_callback_data, amount, user_balance):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    amount_to_pay = amount
    balance_used = 0
    if user_balance > 0:
        if user_balance >= amount:
            balance_used = amount
            amount_to_pay = 0
        else:
            balance_used = user_balance
            amount_to_pay = amount - user_balance

    if amount_to_pay == 0:
        markup.add(types.InlineKeyboardButton(f"Оплата с баланса (использовано {balance_used} ₽)", callback_data=f"pay_balance_{period_callback_data}_{amount}"))
    else:
        markup.add(types.InlineKeyboardButton(f"Оплата с баланса + картой (Баланс: {balance_used} ₽, Доплата: {amount_to_pay} ₽)", callback_data=f"pay_balance_card_{period_callback_data}_{amount}"))
        markup.add(types.InlineKeyboardButton(f"Оплата картой ({amount} ₽)", callback_data=f"pay_card_{period_callback_data}_{amount}"))
    
    markup.add(types.InlineKeyboardButton(f"Оплата Telegram Stars ({amount} Stars)", callback_data=f"pay_stars_{period_callback_data}_{amount}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="buy_vpn"))
    return markup

def my_account_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Запросить конфиг", callback_data="request_config"),
        types.InlineKeyboardButton("Продлить подписку", callback_data="buy_vpn"),
        types.InlineKeyboardButton("Назад", callback_data="main_menu")
    )
    return markup

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
            'balance': REFERRAL_BONUS_NEW_USER,
            'subscription_end': None,
            'referred_by': referred_by_id,
            'username': username,
            'first_name': first_name,
            'referrals_count': 0,
            'used_configs': {}
        }
        save_data('users.json', users_db)
        bot.send_message(message.chat.id, f"Привет! Добро пожаловать в VPN Bot! Вам начислено {REFERRAL_BONUS_NEW_USER} ₽ на баланс за регистрацию.",
                         reply_markup=main_menu_keyboard(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "Привет! Снова добро пожаловать в VPN Bot!",
                         reply_markup=main_menu_keyboard(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    if call.data == "main_menu":
        bot.edit_message_text("Главное меню:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=main_menu_keyboard(user_id))
    
    elif call.data == "buy_vpn":
        bot.edit_message_text("Выберите срок подписки:", chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=buy_vpn_keyboard())
    
    elif call.data.startswith("choose_period_"):
        period_data = call.data.replace("choose_period_", "")
        amount = 0
        if period_data == "1_month":
            amount = PRICE_MONTH
        elif period_data == "2_months":
            amount = PRICE_2_MONTHS
        elif period_data == "3_months":
            amount = PRICE_3_MONTHS
        
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        
        bot.edit_message_text(f"Вы выбрали подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}. "
                              f"К оплате: {amount} ₽.\nВаш баланс: {user_balance} ₽.\nВыберите способ оплаты:",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=payment_methods_keyboard(period_data, amount, user_balance))

    elif call.data.startswith("pay_balance_card_") or call.data.startswith("pay_card_"):
        parts = call.data.split('_')
        period_data = parts[2] + '_' + parts[3]
        amount_needed = int(parts[4])

        payment_id = generate_payment_id()
        payments_db[payment_id] = {
            'user_id': user_id,
            'amount': amount_needed,
            'status': 'pending',
            'screenshot_id': None,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'period': period_data,
            'method': 'card'
        }
        
        balance_used = 0
        amount_to_transfer = amount_needed
        
        if call.data.startswith("pay_balance_card_"):
            user_balance = users_db.get(user_id, {}).get('balance', 0)
            if user_balance > 0:
                balance_used = min(user_balance, amount_needed)
                amount_to_transfer = amount_needed - balance_used
                payments_db[payment_id]['balance_used'] = balance_used
        
        save_data('payments.json', payments_db)

        if amount_to_transfer > 0:
            bot.edit_message_text(f"Для оплаты {amount_needed} ₽ за подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}:"
                                f"\n\n1. Переведите {amount_to_transfer} ₽ на карту: `{CARD_NUMBER}`"
                                f"\nДержатель: `{CARD_HOLDER}`"
                                f"\n\n2. **ОБЯЗАТЕЛЬНО** отправьте скриншот перевода в этот чат."
                                f"\n\nПосле получения скриншота администратор проверит платеж и подтвердит вашу подписку."
                                f"\n**Ваш платеж может быть подтвержден с задержкой, ожидайте, пожалуйста.**",
                                chat_id=call.message.chat.id, message_id=call.message.message_id,
                                parse_mode='Markdown')
            
            bot.send_message(ADMIN_ID, 
                            f"🔔 Новый платеж на {amount_to_transfer} ₽ (всего {amount_needed} ₽) от @{call.from_user.username} (ID: {user_id}) за {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}. "
                            f"Баланс пользователя использован на {balance_used} ₽. Ожидает скриншот.", 
                            reply_markup=main_menu_keyboard(ADMIN_ID))
        else: # Сюда мы не должны попасть, если amount_to_transfer == 0, для этого pay_balance_...
            bot.edit_message_text("Ошибка в логике оплаты. Обратитесь в поддержку.", chat_id=call.message.chat.id, message_id=call.message.message_id)


    elif call.data.startswith("pay_balance_"):
        parts = call.data.split('_')
        period_data = parts[2] + '_' + parts[3]
        amount_needed = int(parts[4])

        user_info = users_db.get(user_id, {})
        user_balance = user_info.get('balance', 0)

        if user_balance >= amount_needed:
            users_db[user_id]['balance'] -= amount_needed
            
            current_end = user_info.get('subscription_end')
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

            payment_id = generate_payment_id()
            payments_db[payment_id] = {
                'user_id': user_id,
                'amount': amount_needed,
                'status': 'confirmed',
                'screenshot_id': None,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period': period_data,
                'method': 'balance',
                'balance_used': amount_needed
            }
            save_data('payments.json', payments_db)

            bot.edit_message_text(f"✅ Ваша подписка на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')} успешно оплачена с баланса!\n"
                                f"Ваша подписка активна до: {new_end.strftime('%d.%m.%Y %H:%M')}\n"
                                f"Текущий баланс: {users_db[user_id]['balance']} ₽.\n"
                                f"Можете запросить конфиг в личном кабинете.",
                                chat_id=call.message.chat.id, message_id=call.message.message_id,
                                reply_markup=main_menu_keyboard(user_id))
            bot.send_message(ADMIN_ID, 
                             f"🔔 Пользователь @{call.from_user.username} (ID: {user_id}) оплатил подписку на {period_data.replace('_', ' ').replace('month', 'месяц').replace('s', 'а')} с баланса ({amount_needed} ₽).",
                             reply_markup=main_menu_keyboard(ADMIN_ID))
        else:
            bot.edit_message_text("Недостаточно средств на балансе для полной оплаты. Пожалуйста, выберите оплату картой.",
                                chat_id=call.message.chat.id, message_id=call.message.message_id,
                                reply_markup=buy_vpn_keyboard())

    elif call.data.startswith("pay_stars_"):
        parts = call.data.split('_')
        period_data = parts[2] + '_' + parts[3]
        amount_needed = int(parts[4])
        
        bot.edit_message_text(f"Оплата Telegram Stars пока находится в разработке! "
                              f"Пожалуйста, используйте оплату картой.\n\n"
                              f"К оплате: {amount_needed} Stars.",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=buy_vpn_keyboard())

    elif call.data == "my_account":
        user_info = users_db.get(user_id, {})
        subscription_end = user_info.get('subscription_end')
        balance = user_info.get('balance', 0)

        status_text = "Нет активной подписки"
        remaining_days = "0"
        if subscription_end:
            end_date = datetime.datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
            if end_date > datetime.datetime.now():
                status_text = f"Подписка активна до: {end_date.strftime('%d.%m.%Y %H:%M')}"
                time_left = end_date - datetime.datetime.now()
                remaining_days = str(time_left.days)
            else:
                status_text = "Подписка истекла"
                users_db[user_id]['subscription_end'] = None
                save_data('users.json', users_db)

        bot.edit_message_text(f"👤 Ваш личный кабинет:\n\n"
                              f"Статус подписки: {status_text}\n"
                              f"Осталось дней: {remaining_days}\n"
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
                
                user_used_configs = users_db[user_id].get('used_configs', {})
                current_subscription_period = ""
                
                # Определяем текущий период подписки пользователя
                time_left_days = (end_date - datetime.datetime.now()).days
                if time_left_days >= 89: # 3 месяца (примерно)
                    current_subscription_period = '3_months'
                elif time_left_days >= 59: # 2 месяца (примерно)
                    current_subscription_period = '2_months'
                elif time_left_days >= 29: # 1 месяц (примерно)
                    current_subscription_period = '1_month'
                
                if not current_subscription_period:
                     bot.send_message(call.message.chat.id, "Не могу определить ваш текущий период подписки. Обратитесь в поддержку.")
                     bot.send_message(call.message.chat.id, "Что еще вы хотите сделать?", reply_markup=main_menu_keyboard(user_id))
                     return

                available_configs_for_period = [cfg for cfg in configs_db.get(current_subscription_period, []) if cfg.get('active', True)]
                
                # Ищем неиспользованный конфиг
                found_config = None
                config_index = -1
                for i, config in enumerate(available_configs_for_period):
                    if config.get('id') not in user_used_configs.get(current_subscription_period, []):
                        found_config = config
                        config_index = i
                        break

                if found_config:
                    bot.send_message(call.message.chat.id, "Вот ваш VPN конфиг:")
                    if found_config.get('image'):
                        bot.send_photo(call.message.chat.id, found_config['image'])
                    bot.send_message(call.message.chat.id, 
                                     f"**Имя:** {found_config['name']}\n"
                                     f"**Код:** `{found_config['code']}`\n"
                                     f"**Ссылка:** {found_config['link']}",
                                     parse_mode='Markdown')
                    
                    if current_subscription_period not in users_db[user_id]['used_configs']:
                        users_db[user_id]['used_configs'][current_subscription_period] = []
                    users_db[user_id]['used_configs'][current_subscription_period].append(found_config['id'])
                    
                    # Деактивируем конфиг, чтобы его не выдавали повторно другим
                    # NOTE: Это работает только если у каждого конфига есть уникальный 'id'
                    # Если ID нет, то нужно искать по другим полям или выдавать всегда тот же, но это не то, что вы просили.
                    # Сейчас полагаемся на 'id' в конфиге
                    for cfg_list in configs_db.values():
                        for cfg in cfg_list:
                            if cfg.get('id') == found_config.get('id'):
                                cfg['active'] = False
                                break
                    
                    save_data('users.json', users_db)
                    save_data('configs.json', configs_db)

                else:
                    bot.send_message(call.message.chat.id, "К сожалению, сейчас нет доступных VPN-конфигов для вашего периода подписки. Обратитесь в поддержку.")
            else:
                bot.send_message(call.message.chat.id, "Ваша подписка истекла. Пожалуйста, продлите ее.")
        else:
            bot.send_message(call.message.chat.id, "У вас нет активной подписки. Приобретите ее, чтобы получить конфиг.")
        
        bot.send_message(call.message.chat.id, "Что еще вы хотите сделать?", reply_markup=main_menu_keyboard(user_id))

    elif call.data == "support":
        bot.edit_message_text(f"Для связи с поддержкой напишите @Gl1ch555.\n"
                              f"Постараемся ответить как можно скорее.",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=main_menu_keyboard(user_id))

    elif call.data == "referral_system":
        referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        user_info = users_db.get(user_id, {})
        referrals_count = user_info.get('referrals_count', 0)
        balance = user_info.get('balance', 0)

        bot.edit_message_text(f"🤝 **Реферальная система**\n\n"
                              f"Приглашайте друзей и получайте бонусы!\n"
                              f"За каждого приглашенного пользователя, который зарегистрируется по вашей ссылке, "
                              f"вы получите {REFERRAL_BONUS_RUB} ₽ на баланс и {REFERRAL_BONUS_DAYS} дней к активной подписке.\n"
                              f"Ваш друг получит {REFERRAL_BONUS_NEW_USER} ₽ на баланс при регистрации.\n\n"
                              f"Ваша реферальная ссылка: `{referral_link}`\n\n"
                              f"Количество ваших рефералов: {referrals_count}\n"
                              f"Ваш реферальный баланс: {balance} ₽",
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              parse_mode='Markdown', reply_markup=main_menu_keyboard(user_id))

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
                        status = "Активен" if config.get('active', True) else "Использован"
                        message_text += f"  {i+1}. Имя: {config['name']}, Код: `{config['code']}` (ID: {config.get('id', 'N/A')}), Статус: {status}\n"
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
            bot.send_message(call.message.chat.id, "Введите период и ID конфига для удаления (например, `1_month 0` для первого конфига на 1 месяц, где 0 это индекс). "
                                                  "Для более точного удаления по ID конфига введите `id <ID_конфига>` (например, `id 12345`).")
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
                    caption_text = f"Платеж ID: {payment_id}\n" \
                                   f"От: @{user_payment.get('username', 'N/A')} (ID: {p_data['user_id']})\n" \
                                   f"Сумма: {p_data['amount']} ₽\n" \
                                   f"Период: {p_data['period'].replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}\n" \
                                   f"Время: {p_data['timestamp']}"
                    if p_data.get('balance_used'):
                        caption_text += f"\nИспользовано баланса: {p_data['balance_used']} ₽"

                    bot.send_photo(ADMIN_ID, p_data['screenshot_id'], 
                                   caption=caption_text,
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
                amount_paid = payments_db[payment_id]['amount']
                balance_used = payments_db[payment_id].get('balance_used', 0)
                
                if target_user_id in users_db:
                    # Списываем баланс, если использовался
                    if balance_used > 0:
                        users_db[target_user_id]['balance'] -= balance_used

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
                    end_date = datetime.datetime.strptime(u_data['subscription_end'], '%Y-%m-%d %H:%M:%S')
                    if end_date > datetime.datetime.now():
                        sub_end_str = end_date.strftime('%d.%m.%Y %H:%M')
                        time_left = end_date - datetime.datetime.now()
                        sub_end_str += f" ({time_left.days} дн.)"
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

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = str(message.from_user.id)
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
        
        caption_text = f"❗️ Новый скриншот платежа ID: {pending_payment}\n" \
                       f"От: @{message.from_user.username} (ID: {user_id})\n" \
                       f"Сумма: {payments_db[pending_payment]['amount']} ₽\n" \
                       f"Период: {payments_db[pending_payment]['period'].replace('_', ' ').replace('month', 'месяц').replace('s', 'а')}\n" \
                       f"Время: {payments_db[pending_payment]['timestamp']}"
        if payments_db[pending_payment].get('balance_used'):
            caption_text += f"\nИспользовано баланса: {payments_db[pending_payment]['balance_used']} ₽"

        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                       caption=caption_text,
                       reply_markup=confirm_payments_keyboard(pending_payment))
    else:
        bot.send_message(message.chat.id, "Не могу найти ожидающий платеж для этого скриншота. "
                                         "Возможно, вы уже отправили скриншот или не инициировали платеж. "
                                         "Если возникли проблемы, обратитесь в поддержку (@Gl1ch555).")

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
        
        new_config_id = str(int(time.time() * 1000) + len(configs_db.get(period, [])))

        new_config = {
            'id': new_config_id,
            'name': name,
            'image': image_url if image_url.lower() != 'none' else None,
            'code': code,
            'link': link,
            'active': True
        }
        
        if period not in configs_db:
            configs_db[period] = []
        configs_db[period].append(new_config)
        save_data('configs.json', configs_db)
        
        bot.send_message(user_id, f"Конфиг '{name}' (ID: {new_config_id}) успешно добавлен!", reply_markup=admin_keyboard())
    except Exception as e:
        bot.send_message(user_id, f"Ошибка при добавлении конфига: {e}\nПопробуйте еще раз.", reply_markup=admin_keyboard())

def process_delete_config(message):
    user_id = str(message.from_user.id)
    if user_id != str(ADMIN_ID): return

    try:
        parts = message.text.split()
        if len(parts) < 2:
            raise ValueError("Некорректный формат. Используйте `период ID` или `id <ID_конфига>`")
        
        if parts[0].lower() == 'id':
            target_config_id = parts[1]
            found = False
            for period, configs_list in configs_db.items():
                for i, config in enumerate(configs_list):
                    if config.get('id') == target_config_id:
                        deleted_config = configs_list.pop(i)
                        found = True
                        break
                if found: break
            
            if found:
                save_data('configs.json', configs_db)
                bot.send_message(user_id, f"Конфиг '{deleted_config.get('name', 'N/A')}' (ID: {target_config_id}) успешно удален.", reply_markup=admin_keyboard())
            else:
                bot.send_message(user_id, f"Конфиг с ID '{target_config_id}' не найден.", reply_markup=admin_keyboard())

        else: # Удаление по индексу
            period, config_id_str = parts[0], parts[1]
            config_id = int(config_id_str)

            if period not in configs_db:
                raise ValueError(f"Период '{period}' не найден.")
            
            if not (0 <= config_id < len(configs_db[period])):
                raise ValueError("Некорректный ID конфига для этого периода (индекс).")
            
            deleted_config = configs_db[period].pop(config_id)
            save_data('configs.json', configs_db)
            
            bot.send_message(user_id, f"Конфиг '{deleted_config['name']}' (ID: {deleted_config.get('id', 'N/A')}) успешно удален из периода '{period}'.", reply_markup=admin_keyboard())
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
                               "`used_configs <период> reset` (сбросить использованные конфиги для периода, например `used_configs 1_month reset`)\n"
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
        elif action == 'used_configs' and value and value.endswith('reset'):
            period_to_reset = value.split()[0]
            if period_to_reset in users_db[target_user_id].get('used_configs', {}):
                users_db[target_user_id]['used_configs'][period_to_reset] = []
                # Активируем конфиги, которые были привязаны к этому пользователю для этого периода
                for cfg in configs_db.get(period_to_reset, []):
                    if not cfg.get('active', True) and cfg.get('id') not in users_db[target_user_id]['used_configs'][period_to_reset]:
                        cfg['active'] = True
                save_data('configs.json', configs_db)
                bot.send_message(user_id, f"Использованные конфиги для периода '{period_to_reset}' пользователя {target_user_id} сброшены.", reply_markup=admin_keyboard())
                bot.send_message(target_user_id, f"Администратор сбросил список использованных вами конфигов для периода '{period_to_reset}'.")
            else:
                bot.send_message(user_id, f"У пользователя {target_user_id} нет использованных конфигов для периода '{period_to_reset}' или период неверный.", reply_markup=admin_keyboard())
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
            time.sleep(0.1)
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {uid}: {e}")
            failed_count += 1
    
    bot.send_message(user_id, f"Рассылка завершена. Отправлено {sent_count} сообщений, не отправлено {failed_count}.", reply_markup=admin_keyboard())

print("Бот запущен...")
bot.polling(none_stop=True)
