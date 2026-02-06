import json
import pymongo
import os
import sys
from datetime import datetime

# Configuration
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "vpn_bot"

if not MONGO_URI:
    print("Please set MONGO_URI environment variable.")
    print("Example: export MONGO_URI='mongodb+srv://<user>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority'")
    sys.exit(1)

def load_json(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found. Skipping.")
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def migrate():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # Migrate Users
    users_data = load_json('users.json')
    if users_data:
        print(f"Migrating {len(users_data)} users...")
        users_col = db['users']
        for user_id, user_info in users_data.items():
            user_doc = {
                "_id": str(user_id),
                "balance": user_info.get('balance', 0),
                "subscription_end": user_info.get('subscription_end'),
                "first_name": user_info.get('first_name'),
                "username": user_info.get('username'),
                "referrals_count": user_info.get('referrals_count', 0),
                "referred_by": user_info.get('referred_by'),
                "used_configs": user_info.get('used_configs', []),
                "migrated_at": datetime.now()
            }
            users_col.update_one({"_id": str(user_id)}, {"$set": user_doc}, upsert=True)
        print("Users migration complete.")

    # Migrate Configs
    configs_data = load_json('configs.json')
    if configs_data:
        print("Migrating configs...")
        configs_col = db['configs']
        count = 0
        for period, configs_list in configs_data.items():
            for config in configs_list:
                config_doc = {
                    "period": period,
                    "name": config.get('name'),
                    "link": config.get('link'),
                    "code": config.get('code'),
                    "used": config.get('used', False),
                    "migrated_at": datetime.now()
                }
                # Use link as unique identifier if possible, or composite key
                filter_query = {"link": config.get('link')}
                configs_col.update_one(filter_query, {"$set": config_doc}, upsert=True)
                count += 1
        print(f"Migrated {count} configs.")

    # Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        print(f"Migrating {len(payments_data)} payments...")
        payments_col = db['payments']
        for payment_id, payment_info in payments_data.items():
            payment_doc = {
                "_id": str(payment_id),
                "user_id": str(payment_info.get('user_id')),
                "amount": payment_info.get('amount'),
                "status": payment_info.get('status'),
                "method": payment_info.get('method'),
                "timestamp": payment_info.get('timestamp'),
                "type": payment_info.get('type'),
                "migrated_at": datetime.now()
            }
            payments_col.update_one({"_id": str(payment_id)}, {"$set": payment_doc}, upsert=True)
        print("Payments migration complete.")

    print("Migration finished successfully.")

if __name__ == "__main__":
    migrate()
