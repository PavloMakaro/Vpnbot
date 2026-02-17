import json
import os
import pymongo
from datetime import datetime

# CONFIGURATION
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

def migrate():
    print("Starting migration...")

    # Load JSON files
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        print(f"Loaded {len(users_data)} users.")
    except FileNotFoundError:
        users_data = {}
        print("users.json not found.")

    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            configs_data = json.load(f)
        print(f"Loaded configs.")
    except FileNotFoundError:
        configs_data = {}
        print("configs.json not found.")

    try:
        with open('payments.json', 'r', encoding='utf-8') as f:
            payments_data = json.load(f)
        print(f"Loaded {len(payments_data)} payments.")
    except FileNotFoundError:
        payments_data = {}
        print("payments.json not found.")

    # Connect to MongoDB
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # 1. Migrate Users
    users_coll = db['users']
    if users_data:
        users_bulk = []
        for user_id, user_info in users_data.items():
            # Convert subscription_end string to datetime object if present
            sub_end = user_info.get('subscription_end')
            if sub_end:
                try:
                    sub_end = datetime.strptime(sub_end, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass # Keep as string or None

            doc = {
                '_id': str(user_id),
                'username': user_info.get('username'),
                'first_name': user_info.get('first_name'),
                'balance': user_info.get('balance', 0),
                'subscription_end': sub_end,
                'referrals_count': user_info.get('referrals_count', 0),
                'referred_by': user_info.get('referred_by'),
                'used_configs': user_info.get('used_configs', [])
            }
            users_bulk.append(pymongo.UpdateOne({'_id': str(user_id)}, {'$set': doc}, upsert=True))

        if users_bulk:
            result = users_coll.bulk_write(users_bulk)
            print(f"Users migrated: {result.upserted_count} inserted, {result.modified_count} updated.")

    # 2. Migrate Configs
    configs_coll = db['configs']
    if configs_data:
        configs_bulk = []
        for period, config_list in configs_data.items():
            for conf in config_list:
                doc = {
                    'period': period,
                    'name': conf.get('name'),
                    'link': conf.get('link'),
                    'code': conf.get('code'),
                    'used': conf.get('used', False),
                    # We might want to add 'imported_at': datetime.now()
                }
                # Use link as unique identifier to prevent duplicates?
                # Or just insert. Let's use link as unique key for upsert.
                if conf.get('link'):
                    configs_bulk.append(pymongo.UpdateOne({'link': conf.get('link')}, {'$set': doc}, upsert=True))

        if configs_bulk:
            result = configs_coll.bulk_write(configs_bulk)
            print(f"Configs migrated: {result.upserted_count} inserted, {result.modified_count} updated.")

    # 3. Migrate Payments
    payments_coll = db['payments']
    if payments_data:
        payments_bulk = []
        for payment_id, p_data in payments_data.items():
            doc = {
                '_id': str(payment_id),
                'user_id': str(p_data.get('user_id')),
                'amount': p_data.get('amount'),
                'status': p_data.get('status'),
                'timestamp': p_data.get('timestamp'), # Keep string or parse
                'method': p_data.get('method'),
                'type': p_data.get('type')
            }
            payments_bulk.append(pymongo.UpdateOne({'_id': str(payment_id)}, {'$set': doc}, upsert=True))

        if payments_bulk:
            result = payments_coll.bulk_write(payments_bulk)
            print(f"Payments migrated: {result.upserted_count} inserted, {result.modified_count} updated.")

    print("Migration complete.")

if __name__ == "__main__":
    if "mongodb+srv" in MONGO_URI and "<username>" in MONGO_URI:
         print("Please set MONGO_URI environment variable with your actual connection string.")
    else:
        migrate()
