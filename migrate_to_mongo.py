import json
import os
import sys
from datetime import datetime

try:
    from pymongo import MongoClient, UpdateOne
except ImportError:
    print("pymongo not installed. Please run: pip install pymongo")
    sys.exit(1)

# Configuration
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "vpn_bot"

if not MONGO_URI:
    print("Please set MONGO_URI environment variable.")
    print("Example: export MONGO_URI='mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority'")
    sys.exit(1)

def load_json(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found. Skipping.")
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def migrate():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    print(f"Connected to MongoDB: {DB_NAME}")

    # 1. Migrate Users
    users_data = load_json('users.json')
    if users_data:
        print(f"Migrating {len(users_data)} users...")
        users_ops = []
        for user_id, data in users_data.items():
            # Ensure proper types
            data['_id'] = str(user_id) # Use string ID for Telegram

            # Convert referral data structure if needed
            if 'referrals_count' in data:
                data['referral'] = {
                    'count': data.pop('referrals_count', 0),
                    'earnings': 0 # Legacy data doesn't track earnings separately usually
                }

            # Upsert operation
            users_ops.append(
                UpdateOne({'_id': data['_id']}, {'$set': data}, upsert=True)
            )

        if users_ops:
            result = db.users.bulk_write(users_ops)
            print(f"Users: {result.upserted_count} inserted, {result.modified_count} updated.")

    # 2. Migrate Configs
    configs_data = load_json('configs.json')
    if configs_data:
        print("Migrating configs...")
        configs_ops = []
        total_configs = 0

        for period, config_list in configs_data.items():
            for conf in config_list:
                # Add period field
                conf['period'] = period

                # Check for unique identifier, usually link is unique
                if 'link' in conf:
                    filter_query = {'link': conf['link']}
                    configs_ops.append(
                        UpdateOne(filter_query, {'$set': conf}, upsert=True)
                    )
                    total_configs += 1

        if configs_ops:
            result = db.configs.bulk_write(configs_ops)
            print(f"Configs: {result.upserted_count} inserted, {result.modified_count} updated.")

    # 3. Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        print(f"Migrating {len(payments_data)} payments...")
        payments_ops = []
        for payment_id, data in payments_data.items():
            data['_id'] = payment_id

            payments_ops.append(
                UpdateOne({'_id': payment_id}, {'$set': data}, upsert=True)
            )

        if payments_ops:
            result = db.payments.bulk_write(payments_ops)
            print(f"Payments: {result.upserted_count} inserted, {result.modified_count} updated.")

    print("Migration complete!")

if __name__ == "__main__":
    migrate()
