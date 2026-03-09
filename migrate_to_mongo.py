import json
import os
import pymongo
from pymongo import MongoClient

# Target MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def migrate_users(db, users_data):
    if not users_data:
        print("No user data to migrate.")
        return

    users_coll = db['users']
    for user_id_str, user_info in users_data.items():
        doc = {
            '_id': user_id_str,
            'balance': user_info.get('balance', 0),
            'subscription_end': user_info.get('subscription_end'),
            'referred_by': user_info.get('referred_by'),
            'username': user_info.get('username', 'N/A'),
            'first_name': user_info.get('first_name', 'N/A'),
            'referrals_count': user_info.get('referrals_count', 0),
            'used_configs': user_info.get('used_configs', [])
        }
        users_coll.update_one({'_id': user_id_str}, {'$set': doc}, upsert=True)
    print(f"Migrated {len(users_data)} users.")

def migrate_configs(db, configs_data):
    if not configs_data:
        print("No configs data to migrate.")
        return

    configs_coll = db['configs']
    count = 0
    for period, config_list in configs_data.items():
        for config in config_list:
            doc = {
                'name': config.get('name'),
                'link': config.get('link'),
                'code': config.get('code', ''),
                'used': config.get('used', False),
                'period': period
            }
            # Use link as unique identifier for configs to avoid duplicates if run multiple times
            if doc['link']:
                configs_coll.update_one({'link': doc['link']}, {'$set': doc}, upsert=True)
                count += 1
    print(f"Migrated {count} configs.")

def migrate_payments(db, payments_data):
    if not payments_data:
        print("No payments data to migrate.")
        return

    payments_coll = db['payments']
    for payment_id_str, payment_info in payments_data.items():
        doc = payment_info.copy()
        doc['_id'] = payment_id_str
        payments_coll.update_one({'_id': payment_id_str}, {'$set': doc}, upsert=True)
    print(f"Migrated {len(payments_data)} payments.")

def main():
    print(f"Connecting to MongoDB: {MONGO_URI}")
    # Allow injection of client for testing
    global client
    if 'client' not in globals():
        client = MongoClient(MONGO_URI)

    db = client['vpn_bot']

    users_data = load_data('users.json')
    configs_data = load_data('configs.json')
    payments_data = load_data('payments.json')

    print("Starting migration...")
    migrate_users(db, users_data)
    migrate_configs(db, configs_data)
    migrate_payments(db, payments_data)
    print("Migration complete!")

if __name__ == "__main__":
    main()