import json
import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")

client = None

def get_client():
    global client
    if client is None:
        client = MongoClient(MONGO_URI)
    return client

def migrate_data():
    if not MONGO_URI and client is None:
        print("MONGO_URI environment variable is not set")
        return

    db = get_client()["vpn_bot"]
    users_collection = db["users"]
    configs_collection = db["configs"]
    payments_collection = db["payments"]

    # Migrate users
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            try:
                users_data = json.load(f)
                for user_id, user_info in users_data.items():
                    user_info["_id"] = user_id
                    users_collection.replace_one({"_id": user_id}, user_info, upsert=True)
                print(f"Migrated {len(users_data)} users.")
            except json.JSONDecodeError:
                print("Error decoding users.json")

    # Migrate configs
    if os.path.exists("configs.json"):
        with open("configs.json", "r") as f:
            try:
                configs_data = json.load(f)
                config_count = 0
                for period, configs in configs_data.items():
                    for config in configs:
                        config["period"] = period
                        # If the config doesn't have an _id, MongoDB will generate one
                        configs_collection.insert_one(config)
                        config_count += 1
                print(f"Migrated {config_count} configs.")
            except json.JSONDecodeError:
                print("Error decoding configs.json")

    # Migrate payments
    if os.path.exists("payments.json"):
        with open("payments.json", "r") as f:
            try:
                payments_data = json.load(f)
                for payment_id, payment_info in payments_data.items():
                    payment_info["_id"] = payment_id
                    payments_collection.replace_one({"_id": payment_id}, payment_info, upsert=True)
                print(f"Migrated {len(payments_data)} payments.")
            except json.JSONDecodeError:
                print("Error decoding payments.json")

if __name__ == "__main__":
    migrate_data()
