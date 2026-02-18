import json
import os
import pymongo
from datetime import datetime

# Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://YOUR_MONGO_URI")
DB_NAME = "vpn_bot"

def load_json(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def migrate():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]

    print(f"Connected to {DB_NAME} at {MONGO_URI}...")

    # Migrate Users
    users_data = load_json('users.json')
    if users_data:
        users_bulk = []
        for user_id, data in users_data.items():
            # Transform data
            doc = {
                "_id": user_id,
                **data
            }
            # Fix date format if needed
            if 'subscription_end' in doc and doc['subscription_end']:
                try:
                    doc['subscription_end'] = datetime.strptime(doc['subscription_end'], '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            users_bulk.append(doc)

        if users_bulk:
            try:
                # Use insert_many with ordered=False to skip existing (or use replace_one in loop for upsert)
                # Ideally, clear collection first or use update_one with upsert=True
                # For migration, we assume empty DB or overwrite
                db.users.insert_many(users_bulk, ordered=False)
                print(f"Migrated {len(users_bulk)} users.")
            except pymongo.errors.BulkWriteError as bwe:
                print(f"Some users already exist: {bwe.details['nInserted']} inserted.")

    # Migrate Configs
    configs_data = load_json('configs.json')
    if configs_data:
        configs_bulk = []
        for period, items in configs_data.items():
            for item in items:
                doc = {
                    "period": period,
                    **item
                }
                configs_bulk.append(doc)

        if configs_bulk:
            try:
                db.configs.insert_many(configs_bulk, ordered=False)
                print(f"Migrated {len(configs_bulk)} configs.")
            except Exception as e:
                print(f"Error migrating configs: {e}")

    # Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        payments_bulk = []
        for pid, data in payments_data.items():
            doc = {
                "payment_id": pid, # Rename key to payment_id for consistency
                **data
            }
            payments_bulk.append(doc)

        if payments_bulk:
            try:
                db.payments.insert_many(payments_bulk, ordered=False)
                print(f"Migrated {len(payments_bulk)} payments.")
            except Exception as e:
                print(f"Error migrating payments: {e}")

    print("Migration complete.")

if __name__ == "__main__":
    migrate()
