import json
import os
import pymongo
from typing import Optional

# Allow injecting mock client for testing
client: Optional[pymongo.MongoClient] = None

def get_db():
    global client
    if client is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        client = pymongo.MongoClient(mongo_uri)
    return client["vpn_bot"]

def load_json_file(filename):
    try:
        # Consolidation: use os.stat to check file existence and size efficiently
        stat = os.stat(filename)
        if stat.st_size == 0:
            return {}
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except OSError:
        # File doesn't exist
        return {}
    except json.JSONDecodeError:
        return {}

def migrate_users(db):
    users_data = load_json_file('users.json')
    if not users_data:
        return

    users_coll = db["users"]
    operations = []

    for uid, user_info in users_data.items():
        doc = {"_id": uid}
        doc.update(user_info)
        operations.append(pymongo.UpdateOne({"_id": uid}, {"$set": doc}, upsert=True))

    if operations:
        users_coll.bulk_write(operations)

def migrate_configs(db):
    configs_data = load_json_file('configs.json')
    if not configs_data:
        return

    configs_coll = db["configs"]
    operations = []

    for period, config_list in configs_data.items():
        for config in config_list:
            doc = config.copy()
            doc["period"] = period
            # Use link as unique identifier for config to avoid duplicates during migration
            operations.append(pymongo.UpdateOne({"link": config["link"]}, {"$set": doc}, upsert=True))

    if operations:
        configs_coll.bulk_write(operations)

def migrate_payments(db):
    payments_data = load_json_file('payments.json')
    if not payments_data:
        return

    payments_coll = db["payments"]
    operations = []

    for pid, payment_info in payments_data.items():
        doc = payment_info.copy()
        if "payment_id" not in doc:
            doc["payment_id"] = pid
        operations.append(pymongo.UpdateOne({"payment_id": doc["payment_id"]}, {"$set": doc}, upsert=True))

    if operations:
        payments_coll.bulk_write(operations)

def run_migration():
    db = get_db()
    migrate_users(db)
    migrate_configs(db)
    migrate_payments(db)
    print("Migration completed successfully.")

if __name__ == "__main__":
    run_migration()
