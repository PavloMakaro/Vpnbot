import json
import os
import argparse
from pymongo import MongoClient

# For testing with mongomock, we need to allow injecting the client
client = None

def get_client(uri: str):
    global client
    if client is None:
        client = MongoClient(uri)
    return client

def load_json(filepath: str) -> dict:
    if not os.path.exists(filepath):
        print(f"File {filepath} not found, skipping.")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in {filepath}: {e}")
        return {}
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return {}

def migrate_users(db, users_data: dict):
    if not users_data:
        return 0

    users_collection = db.users
    ops_count = 0
    for user_id, user_info in users_data.items():
        doc = {
            '_id': user_id,
            'balance': user_info.get('balance', 0),
            'subscription_end': user_info.get('subscription_end'),
            'referred_by': user_info.get('referred_by'),
            'username': user_info.get('username', ''),
            'first_name': user_info.get('first_name', ''),
            'referrals_count': user_info.get('referrals_count', 0),
            'used_configs': user_info.get('used_configs', [])
        }
        users_collection.update_one({'_id': user_id}, {'$set': doc}, upsert=True)
        ops_count += 1
    return ops_count

def migrate_configs(db, configs_data: dict):
    if not configs_data:
        return 0

    configs_collection = db.configs
    ops_count = 0
    for period, config_list in configs_data.items():
        for config in config_list:
            doc = {
                'period': period,
                'name': config.get('name', ''),
                'link': config.get('link', ''),
                'code': config.get('code', ''),
                'used': config.get('used', False)
            }
            # Avoid duplicate links
            configs_collection.update_one(
                {'link': doc['link']},
                {'$set': doc},
                upsert=True
            )
            ops_count += 1
    return ops_count

def migrate_payments(db, payments_data: dict):
    if not payments_data:
        return 0

    payments_collection = db.payments
    ops_count = 0
    for payment_id, p_data in payments_data.items():
        doc = {
            '_id': payment_id,
            'user_id': p_data.get('user_id'),
            'amount': p_data.get('amount', 0),
            'status': p_data.get('status', 'pending'),
            'method': p_data.get('method', 'yookassa_smart'),
            'timestamp': p_data.get('timestamp'),
            'type': p_data.get('type', 'balance_topup')
        }
        payments_collection.update_one({'_id': payment_id}, {'$set': doc}, upsert=True)
        ops_count += 1
    return ops_count

def run_migration(uri: str, data_dir: str):
    mongo_client = get_client(uri)
    db = mongo_client.vpn_bot

    users_data = load_json(os.path.join(data_dir, 'users.json'))
    configs_data = load_json(os.path.join(data_dir, 'configs.json'))
    payments_data = load_json(os.path.join(data_dir, 'payments.json'))

    print("Starting migration...")
    u_count = migrate_users(db, users_data)
    print(f"Migrated {u_count} users.")

    c_count = migrate_configs(db, configs_data)
    print(f"Migrated {c_count} configs.")

    p_count = migrate_payments(db, payments_data)
    print(f"Migrated {p_count} payments.")

    print("Migration complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Migrate legacy JSON data to MongoDB.")
    parser.add_argument('--uri', type=str, required=True, help="MongoDB connection URI")
    parser.add_argument('--dir', type=str, default='.', help="Directory containing JSON files")
    args = parser.parse_args()

    run_migration(args.uri, args.dir)
