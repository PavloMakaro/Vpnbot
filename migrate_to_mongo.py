import json
import os
import sys
from pymongo import MongoClient

# MongoDB Connection String (Replace with your actual connection string)
MONGO_URI = "mongodb+srv://<username>:<password>@<cluster-url>/?retryWrites=true&w=majority"
DB_NAME = "vpn_bot_db"

def load_json(filename):
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None

def migrate():
    print("Starting migration...")

    users_data = load_json('users.json')
    configs_data = load_json('configs.json')
    payments_data = load_json('payments.json')

    if not users_data and not configs_data and not payments_data:
        print("No JSON data files found (users.json, configs.json, payments.json). Skipping migration.")
        return

    # Connect to MongoDB
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        print(f"Connected to MongoDB: {DB_NAME}")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        sys.exit(1)

    # Migrate Users
    if users_data:
        users_col = db['users']
        bulk_users = []
        for user_id, user_info in users_data.items():
            user_doc = user_info.copy()
            user_doc['_id'] = user_id  # Use Telegram ID as _id
            bulk_users.append(user_doc)

        if bulk_users:
            try:
                # Use update_one with upsert to avoid duplicates if running multiple times
                for user in bulk_users:
                    users_col.update_one({'_id': user['_id']}, {'$set': user}, upsert=True)
                print(f"Migrated {len(bulk_users)} users.")
            except Exception as e:
                print(f"Error migrating users: {e}")

    # Migrate Configs
    if configs_data:
        configs_col = db['configs']
        bulk_configs = []
        for period, config_list in configs_data.items():
            for config in config_list:
                config_doc = config.copy()
                config_doc['period'] = period
                bulk_configs.append(config_doc)

        if bulk_configs:
            try:
                for config in bulk_configs:
                    # Assuming link is unique enough, or use a combination
                    configs_col.update_one({'link': config['link']}, {'$set': config}, upsert=True)
                print(f"Migrated {len(bulk_configs)} configs.")
            except Exception as e:
                print(f"Error migrating configs: {e}")

    # Migrate Payments
    if payments_data:
        payments_col = db['payments']
        bulk_payments = []
        for payment_id, payment_info in payments_data.items():
            payment_doc = payment_info.copy()
            payment_doc['_id'] = payment_id
            bulk_payments.append(payment_doc)

        if bulk_payments:
            try:
                for payment in bulk_payments:
                    payments_col.update_one({'_id': payment['_id']}, {'$set': payment}, upsert=True)
                print(f"Migrated {len(bulk_payments)} payments.")
            except Exception as e:
                print(f"Error migrating payments: {e}")

    print("Migration completed.")

if __name__ == "__main__":
    migrate()
