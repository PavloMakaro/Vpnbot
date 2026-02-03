import telebot
from telebot import types
import json
import time
import datetime
import threading
import os
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from yookassa import Configuration, Payment
import uuid

# Import Database
from database import db

# === CONFIGURATION ===
TOKEN = '8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY'
ADMIN_USERNAME = '@Gl1ch555'
ADMIN_ID = 8320218178
YOOKASSA_SHOP_ID = "1172989"
YOOKASSA_SECRET_KEY = "live_abcZFyD5DDi8YoFafjPEJO_2TjWa5BCIWwWbSJvgrf4"
CURRENCY = "RUB"
# WEBAPP_URL will be used in the bot welcome message.
# Ideally this should be an env var or set manually after deployment.
WEBAPP_URL = "https://your-domain.com"

# YooKassa Setup
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30, 'desc': 'Best for testing'},
    '2_months': {'price': 90, 'days': 60, 'desc': 'Popular choice'},
    '3_months': {'price': 120, 'days': 90, 'desc': 'Best value'}
}

# Initialize Bot
bot = telebot.TeleBot(TOKEN)

# Initialize FastAPI
app = FastAPI()

# Mount Static Files (Frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# === API MODELS ===
class TopupRequest(BaseModel):
    amount: int

class BuyRequest(BaseModel):
    period: str

# === API ENDPOINTS ===
@app.get("/")
def read_root():
    return JSONResponse(content={"message": "VPN Mini App Backend is running. Open index.html in static/"})

@app.get("/api/me")
def get_me(x_telegram_user_id: str = Header(None)):
    if not x_telegram_user_id:
        raise HTTPException(status_code=401, detail="Missing User ID")

    user = db.get_user(x_telegram_user_id)
    if not user:
        # Create user if not exists (first time opening app)
        user = db.create_user(x_telegram_user_id, "Unknown", "User")

    days_left = db.get_subscription_days_left(x_telegram_user_id)

    return {
        "id": x_telegram_user_id,
        "balance": user.get('balance', 0),
        "days_left": days_left,
        "first_name": user.get('first_name'),
        "username": user.get('username')
    }

@app.get("/api/plans")
def get_plans():
    return SUBSCRIPTION_PERIODS

@app.post("/api/buy")
def buy_subscription(req: BuyRequest, x_telegram_user_id: str = Header(None)):
    if not x_telegram_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    period = req.period
    if period not in SUBSCRIPTION_PERIODS:
        raise HTTPException(status_code=400, detail="Invalid period")

    price = SUBSCRIPTION_PERIODS[period]['price']
    user = db.get_user(x_telegram_user_id)

    if user['balance'] < price:
        raise HTTPException(status_code=402, detail="Insufficient balance")

    # Deduct balance
    db.update_user_balance(x_telegram_user_id, -price)

    # Add subscription days
    days = SUBSCRIPTION_PERIODS[period]['days']
    db.add_subscription_days(x_telegram_user_id, days)

    # Assign config
    config = db.get_available_config(period)
    if config:
        db.mark_config_used(period, config['link'])
        db.assign_config_to_user(x_telegram_user_id, config, period, days)

        # Notify user via bot
        try:
            bot.send_message(x_telegram_user_id,
                             f"✅ You purchased {days} days subscription!\n"
                             f"Config: {config['link']}")
        except:
            pass

        return {"success": True, "message": "Subscription active", "config": config['link']}
    else:
        # Admin attention needed
        try:
            bot.send_message(ADMIN_ID, f"⚠️ NO CONFIGS LEFT FOR {period}!")
        except:
            pass
        return {"success": True, "message": "Subscription active, but config generation delayed. Contact support."}

@app.post("/api/topup")
def create_topup(req: TopupRequest, x_telegram_user_id: str = Header(None)):
    if not x_telegram_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    amount = req.amount
    if amount < 50:
        raise HTTPException(status_code=400, detail="Minimum amount is 50")

    try:
        payment = Payment.create({
            "amount": {
                "value": f"{amount}.00",
                "currency": CURRENCY
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/vpni50_bot" # Return to bot
            },
            "capture": True,
            "description": f"Topup {amount} RUB for User {x_telegram_user_id}",
            "metadata": {
                "user_id": x_telegram_user_id,
                "payment_type": "balance_topup"
            }
        }, uuid.uuid4())

        db.create_payment_record(payment.id, x_telegram_user_id, amount)

        return {"confirmation_url": payment.confirmation.confirmation_url}
    except Exception as e:
        print(f"Payment Error: {e}")
        raise HTTPException(status_code=500, detail="Payment provider error")

@app.get("/api/configs")
def get_configs(x_telegram_user_id: str = Header(None)):
    if not x_telegram_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return db.get_user_configs(x_telegram_user_id)


# === BOT HANDLERS ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "User"
    first_name = message.from_user.first_name or "User"

    # Ensure user exists
    db.create_user(user_id, username, first_name)

    markup = types.InlineKeyboardMarkup()
    # Replace with your actual deployed URL
    # For now we use a placeholder or local
    # NOTE: You must update this URL after deploying and getting a public HTTPS URL (e.g. ngrok)
    web_app_url = "https://your-domain.com/static/index.html"

    web_app = types.WebAppInfo(web_app_url)
    markup.add(types.InlineKeyboardButton("🚀 Open VPN App", web_app=web_app))

    bot.send_message(message.chat.id,
                     f"👋 Welcome, {first_name}!\n\n"
                     "Manage your VPN subscription, balance, and configs in our new Mini App.",
                     reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    bot.send_message(message.chat.id, "Admin Panel: Use /add_config [period] [link] or /stats")

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    # Simple stats
    bot.send_message(message.chat.id, "Stats not fully implemented in this version yet.")

@bot.message_handler(commands=['add_config'])
def add_config_handler(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    try:
        parts = message.text.split()
        if len(parts) < 3:
             bot.send_message(message.chat.id, "Usage: /add_config 1_month vmess://...")
             return
        period = parts[1]
        link = parts[2]

        # Use DB method
        db.add_config(period, link)

        bot.send_message(message.chat.id, f"✅ Config added for {period}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")


# === PAYMENT CHECKER ===
def check_payments_loop():
    while True:
        try:
            pending = db.get_pending_payments()
            for pid, data in pending.items():
                try:
                    payment = Payment.find_one(pid)
                    if payment.status == 'succeeded':
                        db.confirm_payment(pid)
                        db.update_user_balance(data['user_id'], data['amount'])
                        bot.send_message(data['user_id'], f"✅ Balance topped up: {data['amount']} RUB")
                        bot.send_message(ADMIN_ID, f"💰 Topup: {data['amount']} RUB by {data['user_id']}")
                    elif payment.status == 'canceled':
                        # Handle cancellation
                        pass
                except Exception as e:
                    pass
                    # Silent error to avoid log spam, real errors printed in main exception
            time.sleep(10)
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(10)

# === RUNNERS ===
def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

def run_bot():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    # Start Payment Checker
    threading.Thread(target=check_payments_loop, daemon=True).start()

    # Start FastAPI in a thread
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    print("🚀 Bot and API started...")
    # Run Bot in main thread
    run_bot()
