import json
import os
import pymongo
from datetime import datetime

# Configure your connection string here or via env variable
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

# Optional explicit client injection for testing (e.g. with mongomock)
client = None

def get_client():
    global client
    if client is None:
        client = pymongo.MongoClient(MONGO_URI)
    return client

def load_json(filepath):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return {}

def migrate_users(db, users_data):
    users_coll = db["users"]
    count = 0
    for user_id, user_info in users_data.items():
        doc = {
            "_id": user_id,
            "username": user_info.get("username", ""),
            "first_name": user_info.get("first_name", ""),
            "balance": user_info.get("balance", 0),
            "referrals_count": user_info.get("referrals_count", 0),
            "referred_by": user_info.get("referred_by"),
            "used_configs": user_info.get("used_configs", [])
        }

        # Convert string dates to datetime objects
        sub_end = user_info.get("subscription_end")
        if sub_end:
            try:
                doc["subscription_end"] = datetime.strptime(sub_end, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                doc["subscription_end"] = None
        else:
            doc["subscription_end"] = None

        users_coll.update_one({"_id": user_id}, {"$set": doc}, upsert=True)
        count += 1

    print(f"Migrated {count} users.")

def migrate_configs(db, configs_data):
    configs_coll = db["configs"]
    count = 0

    # configs_data is typically a dict with periods as keys ('1_month', '2_months', etc.)
    # and lists of config objects as values
    for period, config_list in configs_data.items():
        for config in config_list:
            doc = {
                "name": config.get("name"),
                "link": config.get("link"),
                "code": config.get("code"),
                "used": config.get("used", False),
                "period": period,
                "added_at": datetime.now()
            }
            # Use link as unique identifier to avoid duplicates if run multiple times
            configs_coll.update_one({"link": config.get("link")}, {"$setOnInsert": doc}, upsert=True)
            count += 1

    print(f"Migrated {count} configs.")

def migrate_payments(db, payments_data):
    payments_coll = db["payments"]
    count = 0

    for payment_id, p_info in payments_data.items():
        doc = {
            "_id": payment_id,
            "user_id": p_info.get("user_id"),
            "amount": p_info.get("amount", 0),
            "status": p_info.get("status", "pending"),
            "method": p_info.get("method"),
            "type": p_info.get("type", "balance_topup"),
            "payment_id": p_info.get("payment_id", payment_id)
        }

        timestamp = p_info.get("timestamp")
        if timestamp:
            try:
                doc["timestamp"] = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                doc["timestamp"] = datetime.now()
        else:
            doc["timestamp"] = datetime.now()

        payments_coll.update_one({"_id": payment_id}, {"$set": doc}, upsert=True)
        count += 1

    print(f"Migrated {count} payments.")

def main():
    print("Starting migration to MongoDB Atlas...")
    try:
        c = get_client()
        db = c[DB_NAME]

        users_data = load_json("users.json")
        if users_data:
            migrate_users(db, users_data)

        configs_data = load_json("configs.json")
        if configs_data:
            migrate_configs(db, configs_data)

        payments_data = load_json("payments.json")
        if payments_data:
            migrate_payments(db, payments_data)

        print("Migration completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    main()