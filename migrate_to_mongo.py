import json
import os
import sys
from pymongo import MongoClient

def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File {filename} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {filename}.")
        return {}

def migrate_users(db, users_data):
    users_collection = db['users']
    users_to_insert = []

    for user_id_str, user_info in users_data.items():
        user_doc = {
            '_id': user_id_str,
            'balance': user_info.get('balance', 0),
            'subscription_end': user_info.get('subscription_end'),
            'referred_by': user_info.get('referred_by'),
            'username': user_info.get('username'),
            'first_name': user_info.get('first_name'),
            'referrals_count': user_info.get('referrals_count', 0),
            'used_configs': user_info.get('used_configs', [])
        }
        users_to_insert.append(user_doc)

    if users_to_insert:
        try:
            # Upsert
            for doc in users_to_insert:
                users_collection.update_one({'_id': doc['_id']}, {'$set': doc}, upsert=True)
            print(f"Successfully migrated {len(users_to_insert)} users.")
        except Exception as e:
            print(f"Error migrating users: {e}")

def migrate_configs(db, configs_data):
    configs_collection = db['configs']
    configs_to_insert = []

    for period, config_list in configs_data.items():
        for config in config_list:
            config_doc = {
                'period': period,
                'name': config.get('name'),
                'link': config.get('link'),
                'code': config.get('code'),
                'used': config.get('used', False)
            }
            configs_to_insert.append(config_doc)

    if configs_to_insert:
        try:
            # We don't have a solid unique ID for configs in the JSON, so just insert.
            # If running multiple times, this might duplicate configs.
            # In a real scenario, you'd probably drop or clean before migrate.
            configs_collection.insert_many(configs_to_insert)
            print(f"Successfully migrated {len(configs_to_insert)} configs.")
        except Exception as e:
             print(f"Error migrating configs: {e}")

def migrate_payments(db, payments_data):
    payments_collection = db['payments']
    payments_to_insert = []

    for payment_id, p_data in payments_data.items():
        payment_doc = {
            '_id': payment_id,
            'user_id': p_data.get('user_id'),
            'amount': p_data.get('amount'),
            'status': p_data.get('status'),
            'method': p_data.get('method'),
            'timestamp': p_data.get('timestamp'),
            'type': p_data.get('type'),
            'payment_id': p_data.get('payment_id', payment_id),
            'screenshot_id': p_data.get('screenshot_id'),
            'period': p_data.get('period')
        }
        payments_to_insert.append(payment_doc)

    if payments_to_insert:
        try:
            for doc in payments_to_insert:
                payments_collection.update_one({'_id': doc['_id']}, {'$set': doc}, upsert=True)
            print(f"Successfully migrated {len(payments_to_insert)} payments.")
        except Exception as e:
            print(f"Error migrating payments: {e}")


def main():
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("MONGO_URI environment variable not set.")
        sys.exit(1)

    try:
        client = MongoClient(mongo_uri)
        db = client['vpn_bot']

        print("Starting migration...")

        users_data = load_json('users.json')
        if users_data:
            migrate_users(db, users_data)

        configs_data = load_json('configs.json')
        if configs_data:
            migrate_configs(db, configs_data)

        payments_data = load_json('payments.json')
        if payments_data:
            migrate_payments(db, payments_data)

        print("Migration complete.")

    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    main()
