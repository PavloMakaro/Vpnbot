import json
import os
import pymongo
from datetime import datetime

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

def load_json(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return {}

def migrate():
    print("Starting migration...")

    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DB_NAME]
        print(f"Connected to MongoDB: {DB_NAME}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        return

    # Migrate Users
    users_data = load_json('users.json')
    if users_data:
        users_coll = db['users']
        print(f"Migrating {len(users_data)} users...")

        ops = []
        for user_id, data in users_data.items():
            # Convert string dates to datetime objects if needed
            sub_end = data.get('subscription_end')
            if sub_end:
                try:
                    sub_end = datetime.strptime(sub_end, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    sub_end = None

            doc = {
                'telegram_id': user_id,
                'username': data.get('username'),
                'first_name': data.get('first_name'),
                'balance': data.get('balance', 0),
                'subscription_end': sub_end,
                'referral_count': data.get('referrals_count', 0),
                'referred_by': data.get('referred_by'),
                'used_configs': data.get('used_configs', [])
            }

            ops.append(pymongo.UpdateOne(
                {'telegram_id': user_id},
                {'$set': doc},
                upsert=True
            ))

        if ops:
            result = users_coll.bulk_write(ops)
            print(f"Users migrated: {result.upserted_count} inserted, {result.modified_count} updated.")

    # Migrate Configs
    configs_data = load_json('configs.json')
    if configs_data:
        configs_coll = db['configs']
        print(f"Migrating configs...")

        ops = []
        count = 0
        for period, configs_list in configs_data.items():
            for config in configs_list:
                doc = {
                    'period': period,
                    'name': config.get('name'),
                    'link': config.get('link'),
                    'code': config.get('code'),
                    'used': config.get('used', False),
                    'used_by': None # Need to map this if possible, but JSON structure doesn't seem to link back easily unless we scan users
                }

                # Check if used in users data to populate 'used_by'
                if doc['used']:
                    # This would be slow for large datasets, but fine for migration
                    pass

                ops.append(pymongo.UpdateOne(
                    {'link': config.get('link')},
                    {'$set': doc},
                    upsert=True
                ))
                count += 1

        if ops:
            result = configs_coll.bulk_write(ops)
            print(f"Configs migrated: {result.upserted_count} inserted, {result.modified_count} updated.")

    # Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        payments_coll = db['payments']
        print(f"Migrating {len(payments_data)} payments...")

        ops = []
        for payment_id, data in payments_data.items():
            doc = {
                '_id': payment_id,
                'user_id': data.get('user_id'),
                'amount': data.get('amount'),
                'status': data.get('status'),
                'method': data.get('method'),
                'timestamp': data.get('timestamp'),
                'type': data.get('type')
            }

            ops.append(pymongo.UpdateOne(
                {'_id': payment_id},
                {'$set': doc},
                upsert=True
            ))

        if ops:
            result = payments_coll.bulk_write(ops)
            print(f"Payments migrated: {result.upserted_count} inserted, {result.modified_count} updated.")

    print("Migration completed.")

if __name__ == "__main__":
    migrate()
