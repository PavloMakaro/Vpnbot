import asyncio
import logging
import uuid
import json
import requests
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from yookassa import Configuration, Payment
from fastapi import FastAPI, Request
from uvicorn import Config, Server
import sqlite3

# Настройка
BOT_TOKEN = '8367506028:AAEkOdCm8Lt0ntYzm4_pryrID17XihOXNRw'  # Твой токен
YOOKASSA_SHOP_ID = 'YOUR_SHOP_ID'  # Замени
YOOKASSA_SECRET = 'YOUR_SECRET_KEY'  # Замени
PANEL_URL = 'https://Vpn.play2go.cloud:2053'  # URL панели 3X-UI
PANEL_USERNAME = 'root'  # Логин панели
PANEL_PASSWORD = 'Gl1ch'  # Пароль панели
INBOUND_ID = 2  # Из твоих данных (inbound-443)

# Настройка YooKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET

# Логи
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()  # Для обработки webhook'ов YooKassa

# Состояния для FSM
class PaymentStates(StatesGroup):
    waiting_for_payment = State()

class PaymentDatabase:
    def __init__(self, db_path="payments.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    email TEXT
                )
            ''')
            conn.commit()

    def save_payment(self, payment_id, data):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO payments (payment_id, user_id, email) VALUES (?, ?, ?)",
                (payment_id, data['user_id'], data['email'])
            )
            conn.commit()

    def get_payment(self, payment_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, email FROM payments WHERE payment_id = ?", (payment_id,))
            row = cursor.fetchone()
            if row:
                return {'user_id': row[0], 'email': row[1]}
            return None

    def delete_payment(self, payment_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM payments WHERE payment_id = ?", (payment_id,))
            conn.commit()

payments = PaymentDatabase()

# Логин в 3X-UI
def get_panel_session():
    login_url = f'{PANEL_URL}/panel/api/loginUser'
    try:
        response = requests.post(login_url, json={'username': PANEL_USERNAME, 'password': PANEL_PASSWORD}, verify=False)
        response.raise_for_status()
        return response.json().get('obj', {}).get('token')
    except Exception as e:
        logging.error(f"Ошибка логина в панель: {e}")
        return None

# Добавление клиента в 3X-UI
def add_vless_client(email: str):
    session = get_panel_session()
    if not session:
        return None

    headers = {'Authorization': f'Bearer {session}'}
    add_url = f'{PANEL_URL}/panel/api/inbounds/addClient'
    expiry_time = int((datetime.now() + timedelta(days=30)).timestamp() * 1000)  # 1 месяц
    client_uuid = str(uuid.uuid4())
    client_data = {
        'id': INBOUND_ID,
        'settings': json.dumps({
            'clients': [{
                'id': client_uuid,
                'flow': '',  # Без flow для reality
                'email': email,
                'limitIp': 0,
                'totalGB': 0,
                'expiryTime': expiry_time
            }]
        })
    }
    try:
        response = requests.post(add_url, headers=headers, json=client_data, verify=False)
        response.raise_for_status()
        vless_url = f"vless://{client_uuid}@Vpn.play2go.cloud:443?security=reality&encryption=none&pbk=rMg72yjQaJGOByKY_vkLppjQIeGLJ2Wi2XRYP35PNBg&fp=chrome&sni=ozon.ru&type=tcp&headerType=none#{email}"
        return vless_url
    except Exception as e:
        logging.error(f"Ошибка добавления клиента: {e}")
        return None

# Главное меню
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Купить VPN (50₽/мес)', callback_data='buy_vpn')],
        [InlineKeyboardButton(text='Мои конфиги', callback_data='my_configs')],
        [InlineKeyboardButton(text='Поддержка', url='https://t.me/YOUR_SUPPORT_USERNAME')]
    ])
    return keyboard

# Команда /start
@dp.message(Command('start'))
async def start_handler(message: types.Message):
    await message.answer('Добро пожаловать в VPN бот! Выберите опцию:', reply_markup=get_main_menu())

# Покупка VPN
@dp.callback_query(lambda c: c.data == 'buy_vpn')
async def buy_vpn(callback: types.CallbackQuery, state: FSMContext):
    payment_id = str(uuid.uuid4())
    payment = Payment.create({
        "amount": {"value": "50.00", "currency": "RUB"},
        "confirmation": {"type": "qr"},
        "capture": True,
        "description": "VPN доступ на 1 месяц",
        "receipt": {
            "items": [{"description": "VPN 1 месяц", "quantity": 1, "amount": {"value": "50.00", "currency": "RUB"}, "vat_code": 2}],
            "customer": {"email": f"user_{callback.from_user.id}@example.com"}
        }
    }, idempotence_key=payment_id)

    qr_url = payment.confirmation.confirmation_url

    # Store in DB
    payment_data = {'user_id': callback.from_user.id, 'email': f"user_{callback.from_user.id}_{datetime.now().strftime('%Y%m%d')}"}
    payments.save_payment(payment.id, payment_data)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Оплатить по QR', url=qr_url)],
        [InlineKeyboardButton(text='Проверить оплату', callback_data=f'check_payment_{payment.id}')]
    ])
    await callback.message.answer(f'Оплатите 50₽ по QR-коду:\n{qr_url}', reply_markup=keyboard)
    await state.set_state(PaymentStates.waiting_for_payment)
    await callback.answer()

# Проверка оплаты
@dp.callback_query(lambda c: c.data.startswith('check_payment_'))
async def check_payment(callback: types.CallbackQuery, state: FSMContext):
    payment_id = callback.data.split('_', 2)[-1]
    payment_info = payments.get_payment(payment_id)
    if not payment_info:
        await callback.message.answer('Ошибка: Платеж не найден.')
        return

    payment = Payment.find_one(payment_id)
    if payment.status == 'succeeded':
        email = payment_info['email']
        config = add_vless_client(email)
        if config:
            await callback.message.answer(f'Оплата успешна! Ваш VLESS конфиг:\n<code>{config}</code>\nСрок: 1 месяц.', parse_mode='HTML')
        else:
            await callback.message.answer('Ошибка генерации конфига. Обратитесь в поддержку.')
        payments.delete_payment(payment_id)
        await state.clear()
    else:
        await callback.message.answer('Платеж еще не подтвержден. Попробуйте снова.')
    await callback.answer()

# Webhook для YooKassa
@app.post('/webhook')
async def webhook(request: Request):
    event = await request.json()
    payment = event.get('object')
    if payment and payment.get('status') == 'succeeded':
        payment_id = payment.get('id')
        payment_info = payments.get_payment(payment_id)
        if payment_info:
            email = payment_info['email']
            config = add_vless_client(email)
            if config:
                await bot.send_message(
                    payment_info['user_id'],
                    f'Оплата успешна! Ваш VLESS конфиг:\n<code>{config}</code>\nСрок: 1 месяц.',
                    parse_mode='HTML'
                )
            payments.delete_payment(payment_id)
    return {'status': 'ok'}

# Запуск
async def main():
    # Запуск FastAPI для webhook'ов
    config = Config(app=app, host='0.0.0.0', port=8443)
    server = Server(config)
    asyncio.create_task(server.serve())
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main()) 