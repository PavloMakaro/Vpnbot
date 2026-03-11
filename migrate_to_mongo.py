import json
import pymongo
import os
import sys

# Replace with actual MongoDB URI or pass via environment variable
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "vpn_bot"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return {}

def migrate_users():
    users_data = load_json('users.json')
    if not users_data:
        return

    users_col = db['users']
    for uid, data in users_data.items():
        doc = {
            "_id": str(uid),
            "balance": float(data.get("balance", 0)),
            "subscription_end": data.get("subscription_end"),
            "username": data.get("username", "N/A"),
            "first_name": data.get("first_name", "N/A"),
            "referrals_count": data.get("referrals_count", 0),
            "used_configs": data.get("used_configs", [])
        }
        users_col.update_one({"_id": str(uid)}, {"$set": doc}, upsert=True)

    print(f"Migrated {len(users_data)} users.")

def migrate_configs():
    configs_data = load_json('configs.json')
    if not configs_data:
        return

    configs_col = db['configs']
    count = 0
    for period, config_list in configs_data.items():
        for cfg in config_list:
            doc = {
                "period": period,
                "name": cfg.get("name"),
                "link": cfg.get("link"),
                "code": cfg.get("code", ""),
                "used": cfg.get("used", False)
            }
            # Assuming link is unique
            configs_col.update_one({"link": doc["link"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"Migrated {count} configs.")

def migrate_payments():
    payments_data = load_json('payments.json')
    if not payments_data:
        return

    payments_col = db['payments']
    for pid, data in payments_data.items():
        doc = {
            "_id": str(pid),
            "user_id": str(data.get("user_id")),
            "amount": float(data.get("amount", 0)),
            "status": data.get("status", "unknown"),
            "method": data.get("method", "unknown"),
            "timestamp": data.get("timestamp"),
            "type": data.get("type", "unknown")
        }
        payments_col.update_one({"_id": str(pid)}, {"$set": doc}, upsert=True)

    print(f"Migrated {len(payments_data)} payments.")

if __name__ == "__main__":
    if not os.path.exists("users.json"):
        print("Run script in the directory containing users.json, configs.json, and payments.json.")
        sys.exit(0)

    print("Starting migration to MongoDB...")
    migrate_users()
    migrate_configs()
    migrate_payments()
    print("Migration complete!")
