import json
import os
from pymongo import MongoClient

# Database connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client['vpn']

users_col = db['users']
configs_col = db['configs']
payments_col = db['payments']

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def migrate_users():
    users_data = load_json('users.json')
    if not users_data:
        print("No users to migrate.")
        return

    users_to_insert = []
    for uid, udata in users_data.items():
        doc = {
            "_id": str(uid),
            "username": udata.get("username", "N/A"),
            "first_name": udata.get("first_name", "N/A"),
            "balance": float(udata.get("balance", 0)),
            "subscription_end": udata.get("subscription_end"),
            "referrals_count": int(udata.get("referrals_count", 0)),
            "used_configs": udata.get("used_configs", []),
            "referred_by": udata.get("referred_by")
        }
        users_to_insert.append(doc)

    if users_to_insert:
        # Avoid DuplicateKeyError on multiple runs
        for doc in users_to_insert:
            users_col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        print(f"Migrated {len(users_to_insert)} users.")

def migrate_configs():
    configs_data = load_json('configs.json')
    if not configs_data:
        print("No configs to migrate.")
        return

    configs_to_insert = []
    for period, config_list in configs_data.items():
        for conf in config_list:
            doc = {
                "name": conf.get("name"),
                "link": conf.get("link"),
                "code": conf.get("code"),
                "used": conf.get("used", False),
                "period": period
            }
            # Add uniqueness on link to prevent duplicates
            configs_to_insert.append(doc)

    if configs_to_insert:
        for doc in configs_to_insert:
            configs_col.update_one({"link": doc["link"]}, {"$set": doc}, upsert=True)
        print(f"Migrated {len(configs_to_insert)} configs.")

def migrate_payments():
    payments_data = load_json('payments.json')
    if not payments_data:
        print("No payments to migrate.")
        return

    payments_to_insert = []
    for pid, pdata in payments_data.items():
        doc = {
            "_id": str(pid),
            "user_id": str(pdata.get("user_id")),
            "amount": float(pdata.get("amount", 0)),
            "status": pdata.get("status"),
            "method": pdata.get("method"),
            "timestamp": pdata.get("timestamp"),
            "type": pdata.get("type", "balance_topup")
        }
        payments_to_insert.append(doc)

    if payments_to_insert:
        for doc in payments_to_insert:
            payments_col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        print(f"Migrated {len(payments_to_insert)} payments.")

if __name__ == "__main__":
    print("Starting migration to MongoDB...")
    migrate_users()
    migrate_configs()
    migrate_payments()
    print("Migration complete.")