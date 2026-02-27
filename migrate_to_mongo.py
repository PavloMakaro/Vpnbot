import json
import os
from pymongo import MongoClient
from datetime import datetime

# Connection string to your MongoDB Atlas
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

def migrate_users(db, users_data):
    users_coll = db["users"]
    count = 0
    for user_id, user_info in users_data.items():
        doc = {
            "_id": user_id,
            "username": user_info.get("username"),
            "first_name": user_info.get("first_name"),
            "balance": user_info.get("balance", 0),
            "subscription_end": datetime.strptime(user_info["subscription_end"], '%Y-%m-%d %H:%M:%S') if user_info.get("subscription_end") else None,
            "referrals_count": user_info.get("referrals_count", 0),
            "referred_by": user_info.get("referred_by"),
            "used_configs": user_info.get("used_configs", [])
        }
        users_coll.replace_one({"_id": user_id}, doc, upsert=True)
        count += 1
    print(f"Migrated {count} users.")

def migrate_configs(db, configs_data):
    configs_coll = db["configs"]
    count = 0
    for period, configs_list in configs_data.items():
        for config in configs_list:
            doc = {
                "period": period,
                "name": config.get("name"),
                "link": config.get("link"),
                "code": config.get("code"),
                "used": config.get("used", False),
                "assigned_to": None # Needs logic if we want to map back to user, but usually handled in user doc
            }
            # Only insert if unique link to avoid duplicates
            configs_coll.update_one({"link": config["link"]}, {"$set": doc}, upsert=True)
            count += 1
    print(f"Migrated {count} configs.")

def migrate_payments(db, payments_data):
    payments_coll = db["payments"]
    count = 0
    for payment_id, payment_info in payments_data.items():
        doc = {
            "_id": payment_id,
            "user_id": payment_info.get("user_id"),
            "amount": payment_info.get("amount"),
            "status": payment_info.get("status"),
            "method": payment_info.get("method"),
            "timestamp": datetime.strptime(payment_info["timestamp"], '%Y-%m-%d %H:%M:%S') if payment_info.get("timestamp") else datetime.now(),
            "type": payment_info.get("type")
        }
        payments_coll.replace_one({"_id": payment_id}, doc, upsert=True)
        count += 1
    print(f"Migrated {count} payments.")

def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users_data = json.load(f)
            migrate_users(db, users_data)
    except FileNotFoundError:
        print("users.json not found.")

    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            configs_data = json.load(f)
            migrate_configs(db, configs_data)
    except FileNotFoundError:
        print("configs.json not found.")

    try:
        with open('payments.json', 'r', encoding='utf-8') as f:
            payments_data = json.load(f)
            migrate_payments(db, payments_data)
    except FileNotFoundError:
        print("payments.json not found.")

    print("Migration complete.")

if __name__ == "__main__":
    main()
