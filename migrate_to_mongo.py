import json
import os
from pymongo import MongoClient

# MongoDB connection settings. Can be overridden with env vars.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "vpn_bot")

def migrate_data(client=None):
    if client is None:
        client = MongoClient(MONGO_URI)

    db = client[MONGO_DB_NAME]

    # Collections
    users_collection = db["users"]
    configs_collection = db["configs"]
    payments_collection = db["payments"]

    # Load JSON files
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users_data = json.load(f)
    except FileNotFoundError:
        users_data = {}

    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            configs_data = json.load(f)
    except FileNotFoundError:
        configs_data = {}

    try:
        with open('payments.json', 'r', encoding='utf-8') as f:
            payments_data = json.load(f)
    except FileNotFoundError:
        payments_data = {}

    # Migrate users
    print("Migrating users...")
    for user_id, user_info in users_data.items():
        # Ensure telegram_id is a string
        user_doc = {
            "telegram_id": str(user_id),
            **user_info
        }
        # Update or insert
        users_collection.update_one(
            {"telegram_id": str(user_id)},
            {"$set": user_doc},
            upsert=True
        )

    # Migrate configs
    print("Migrating configs...")
    for period, period_configs in configs_data.items():
        for config in period_configs:
            config_doc = {
                "period": period,
                **config
            }
            # Update or insert by link
            configs_collection.update_one(
                {"link": config["link"]},
                {"$set": config_doc},
                upsert=True
            )

    # Migrate payments
    print("Migrating payments...")
    for payment_id, payment_info in payments_data.items():
        payment_doc = {
            "_id": str(payment_id), # Use Yookassa ID as _id
            **payment_info
        }
        # Ensure user_id is a string if present
        if "user_id" in payment_doc:
            payment_doc["user_id"] = str(payment_doc["user_id"])

        payments_collection.update_one(
            {"_id": str(payment_id)},
            {"$set": payment_doc},
            upsert=True
        )

    print("Migration complete!")

if __name__ == "__main__":
    migrate_data()
