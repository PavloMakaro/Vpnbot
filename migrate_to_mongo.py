import json
import os
from pymongo import MongoClient

# This client variable is expected to be overriden in tests using mongomock
client = None

def get_client():
    global client
    if client is None:
        MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        client = MongoClient(MONGO_URI)
    return client

def load_json(filepath):
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return {}

def migrate_users(db, users_data):
    if not users_data:
        print("No users data to migrate.")
        return

    users_collection = db.users
    bulk_ops = []

    for uid, data in users_data.items():
        user_doc = {
            "_id": str(uid),
            "username": data.get("username", ""),
            "first_name": data.get("first_name", ""),
            "balance": data.get("balance", 0),
            "subscription_end": data.get("subscription_end", None),
            "referrals_count": data.get("referrals_count", 0),
            "used_configs": data.get("used_configs", []),
            "referred_by": data.get("referred_by", None)
        }

        # Upsert
        bulk_ops.append(user_doc)

    if bulk_ops:
        try:
            # We use replace_one with upsert in a loop or just delete and insert many for simplicity in migration
            for op in bulk_ops:
                users_collection.replace_one({"_id": op["_id"]}, op, upsert=True)
            print(f"Successfully migrated {len(bulk_ops)} users.")
        except Exception as e:
            print(f"Error migrating users: {e}")

def migrate_configs(db, configs_data):
    if not configs_data:
        print("No configs data to migrate.")
        return

    configs_collection = db.configs
    bulk_ops = []

    for period, configs in configs_data.items():
        for conf in configs:
            conf_doc = {
                "period": period,
                "name": conf.get("name", ""),
                "link": conf.get("link", ""),
                "code": conf.get("code", ""),
                "used": conf.get("used", False)
            }
            bulk_ops.append(conf_doc)

    if bulk_ops:
        try:
            # Drop existing and insert new
            configs_collection.delete_many({})
            configs_collection.insert_many(bulk_ops)
            print(f"Successfully migrated {len(bulk_ops)} configs.")
        except Exception as e:
            print(f"Error migrating configs: {e}")

def migrate_payments(db, payments_data):
    if not payments_data:
        print("No payments data to migrate.")
        return

    payments_collection = db.payments
    bulk_ops = []

    for pid, data in payments_data.items():
        payment_doc = {
            "_id": str(pid),
            "user_id": str(data.get("user_id", "")),
            "amount": data.get("amount", 0),
            "status": data.get("status", "pending"),
            "method": data.get("method", ""),
            "timestamp": data.get("timestamp", ""),
            "type": data.get("type", ""),
            "payment_id": str(pid)
        }
        bulk_ops.append(payment_doc)

    if bulk_ops:
        try:
            for op in bulk_ops:
                payments_collection.replace_one({"_id": op["_id"]}, op, upsert=True)
            print(f"Successfully migrated {len(bulk_ops)} payments.")
        except Exception as e:
            print(f"Error migrating payments: {e}")

def main():
    print("Starting migration to MongoDB...")
    cli = get_client()
    db = cli["vpn_bot"]

    users_data = load_json("users.json")
    configs_data = load_json("configs.json")
    payments_data = load_json("payments.json")

    migrate_users(db, users_data)
    migrate_configs(db, configs_data)
    migrate_payments(db, payments_data)

    print("Migration complete.")

if __name__ == "__main__":
    main()
