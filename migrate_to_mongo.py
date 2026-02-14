import json
import os
from pymongo import MongoClient
from datetime import datetime

# Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot_db"

def load_json(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def migrate_users(db, users_data):
    users_collection = db['users']
    batch = []
    for user_id, data in users_data.items():
        # Convert string dates to datetime objects if needed, or keep as string and let backend handle it.
        # Ideally, MongoDB stores dates as ISODate.
        subscription_end = data.get('subscription_end')
        if subscription_end:
            try:
                subscription_end = datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass # Keep as string or set to None

        user_doc = {
            '_id': str(user_id), # Telegram ID as _id
            'username': data.get('username'),
            'first_name': data.get('first_name'),
            'balance': data.get('balance', 0),
            'subscription_end': subscription_end,
            'referrals_count': data.get('referrals_count', 0),
            'referred_by': data.get('referred_by'),
            'used_configs': data.get('used_configs', [])
        }
        batch.append(user_doc)

    if batch:
        try:
            users_collection.insert_many(batch, ordered=False)
            print(f"Migrated {len(batch)} users.")
        except Exception as e:
            print(f"Error migrating users: {e}")
    else:
        print("No users to migrate.")

def migrate_configs(db, configs_data):
    configs_collection = db['configs']
    batch = []
    for period, config_list in configs_data.items():
        for config in config_list:
            config_doc = {
                'period': period,
                'name': config.get('name'),
                'link': config.get('link'),
                'code': config.get('code'),
                'used': config.get('used', False)
            }
            batch.append(config_doc)

    if batch:
        try:
            configs_collection.insert_many(batch, ordered=False)
            print(f"Migrated {len(batch)} configs.")
        except Exception as e:
            print(f"Error migrating configs: {e}")
    else:
        print("No configs to migrate.")

def migrate_payments(db, payments_data):
    payments_collection = db['payments']
    batch = []
    for payment_id, data in payments_data.items():
        payment_doc = {
            '_id': payment_id,
            'user_id': data.get('user_id'),
            'amount': data.get('amount'),
            'status': data.get('status'),
            'method': data.get('method'),
            'timestamp': data.get('timestamp'), # Consider converting to datetime
            'type': data.get('type')
        }
        batch.append(payment_doc)

    if batch:
        try:
            payments_collection.insert_many(batch, ordered=False)
            print(f"Migrated {len(batch)} payments.")
        except Exception as e:
            print(f"Error migrating payments: {e}")
    else:
        print("No payments to migrate.")

def main():
    print("Starting migration...")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    users = load_json('users.json')
    migrate_users(db, users)

    configs = load_json('configs.json')
    migrate_configs(db, configs)

    payments = load_json('payments.json')
    migrate_payments(db, payments)

    print("Migration complete.")

if __name__ == "__main__":
    main()
