import json
import os
import sys
from pymongo import MongoClient

# For testing override
client = None

def get_client():
    global client
    if client is None:
        client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    return client

def migrate_users(db):
    try:
        os.stat("users.json")
    except OSError:
        print("users.json not found, skipping.")
        return

    with open("users.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for user_id_str, info in data.items():
        doc = {
            "_id": user_id_str,
            "balance": info.get("balance", 0),
            "subscription_end": info.get("subscription_end"),
            "username": info.get("username", "N/A"),
            "first_name": info.get("first_name", "N/A"),
            "referrals_count": info.get("referrals_count", 0),
            "used_configs": info.get("used_configs", [])
        }
        db.users.update_one({"_id": user_id_str}, {"$set": doc}, upsert=True)
    print(f"Migrated {len(data)} users.")

def migrate_configs(db):
    try:
        os.stat("configs.json")
    except OSError:
        print("configs.json not found, skipping.")
        return

    with open("configs.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for period, configs in data.items():
        for config in configs:
            doc = {
                "period": period,
                "name": config.get("name"),
                "link": config.get("link"),
                "code": config.get("code"),
                "used": config.get("used", False)
            }
            # Avoid duplicates if script run multiple times
            db.configs.update_one(
                {"link": doc["link"]},
                {"$setOnInsert": doc},
                upsert=True
            )
            count += 1
    print(f"Migrated {count} configs.")

def migrate_payments(db):
    try:
        os.stat("payments.json")
    except OSError:
        print("payments.json not found, skipping.")
        return

    with open("payments.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for payment_id, info in data.items():
        doc = {
            "_id": payment_id,
            "user_id": info.get("user_id"),
            "amount": info.get("amount", 0),
            "status": info.get("status", "pending"),
            "method": info.get("method"),
            "timestamp": info.get("timestamp"),
            "type": info.get("type"),
            "payment_id": info.get("payment_id")
        }
        db.payments.update_one({"_id": payment_id}, {"$set": doc}, upsert=True)
    print(f"Migrated {len(data)} payments.")

def main():
    db = get_client().vpn_bot
    print("Starting migration...")
    migrate_users(db)
    migrate_configs(db)
    migrate_payments(db)
    print("Migration complete.")

if __name__ == "__main__":
    main()