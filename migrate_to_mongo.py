import json
import os
import sys
from pymongo import MongoClient

def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# Global client for testing injection
client = None

def migrate():
    global client
    mongo_uri = os.getenv('MONGO_URI')

    if client is None:
        if not mongo_uri:
            print("MONGO_URI environment variable not set.")
            sys.exit(1)
        client = MongoClient(mongo_uri)

    db = client.vpn_bot

    users_col = db.users
    configs_col = db.configs
    payments_col = db.payments

    # Migrate Users
    users_data = load_data('users.json')
    if users_data:
        print(f"Migrating {len(users_data)} users...")
        for user_id_str, user_info in users_data.items():
            user_doc = user_info.copy()
            user_doc['_id'] = user_id_str  # Use string ID as primary key

            # Upsert
            users_col.update_one({'_id': user_id_str}, {'$set': user_doc}, upsert=True)
        print("Users migration complete.")
    else:
        print("No users.json found or empty.")

    # Migrate Configs
    configs_data = load_data('configs.json')
    if configs_data:
        print("Migrating configs...")
        for period, configs in configs_data.items():
            for config in configs:
                config_doc = config.copy()
                config_doc['period'] = period
                # We need a unique identifier, let's use the link
                if 'link' in config_doc:
                    configs_col.update_one({'link': config_doc['link']}, {'$set': config_doc}, upsert=True)
                else:
                    print(f"Warning: Config missing link, inserting directly: {config_doc}")
                    configs_col.insert_one(config_doc)
        print("Configs migration complete.")
    else:
        print("No configs.json found or empty.")

    # Migrate Payments
    payments_data = load_data('payments.json')
    if payments_data:
        print(f"Migrating {len(payments_data)} payments...")
        for payment_id, payment_info in payments_data.items():
            payment_doc = payment_info.copy()
            payment_doc['_id'] = payment_id
            payments_col.update_one({'_id': payment_id}, {'$set': payment_doc}, upsert=True)
        print("Payments migration complete.")
    else:
        print("No payments.json found or empty.")

if __name__ == '__main__':
    migrate()
