import json
import os
import argparse
from datetime import datetime
from pymongo import MongoClient

# Setup default connection string
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "vpn_bot"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON in {filepath}")
            return {}

def migrate_users():
    users_data = load_json('users.json')
    if not users_data:
        print("No user data to migrate.")
        return

    users_col = db['users']
    users_col.delete_many({})  # Clear existing for fresh migration

    docs = []
    for uid_str, user_info in users_data.items():
        doc = {
            '_id': str(uid_str),  # Explicitly cast to string to match JS backend
            'balance': float(user_info.get('balance', 0)),
            'subscription_end': user_info.get('subscription_end'),
            'referred_by': str(user_info['referred_by']) if user_info.get('referred_by') else None,
            'username': user_info.get('username', ''),
            'first_name': user_info.get('first_name', ''),
            'referrals_count': int(user_info.get('referrals_count', 0)),
            'used_configs': user_info.get('used_configs', []),
            'email': user_info.get('email', 'no-email@example.com'),
            'migrated_at': datetime.now()
        }

        # Convert string dates to datetime objects if needed
        if doc['subscription_end']:
            try:
                doc['subscription_end'] = datetime.strptime(doc['subscription_end'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass

        # Fix used_configs dates
        for config in doc['used_configs']:
            if 'issue_date' in config and isinstance(config['issue_date'], str):
                try:
                    config['issue_date'] = datetime.strptime(config['issue_date'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass

        docs.append(doc)

    if docs:
        users_col.insert_many(docs)
        print(f"Migrated {len(docs)} users.")

def migrate_configs():
    configs_data = load_json('configs.json')
    if not configs_data:
        print("No config data to migrate.")
        return

    configs_col = db['configs']
    configs_col.delete_many({})

    docs = []
    for period, config_list in configs_data.items():
        for config in config_list:
            doc = {
                'name': config.get('name', ''),
                'link': config.get('link', ''),
                'code': config.get('code', ''),
                'used': config.get('used', False),
                'period': period,
                'assigned_to': str(config.get('assigned_to')) if config.get('assigned_to') else None,
                'migrated_at': datetime.now()
            }
            docs.append(doc)

    if docs:
        configs_col.insert_many(docs)
        print(f"Migrated {len(docs)} configs.")

def migrate_payments():
    payments_data = load_json('payments.json')
    if not payments_data:
        print("No payment data to migrate.")
        return

    payments_col = db['payments']
    payments_col.delete_many({})

    docs = []
    for payment_id, p_info in payments_data.items():
        doc = {
            '_id': str(payment_id),
            'user_id': str(p_info.get('user_id', '')),
            'amount': float(p_info.get('amount', 0)),
            'status': p_info.get('status', 'pending'),
            'method': p_info.get('method', 'yookassa_smart'),
            'type': p_info.get('type', 'balance_topup'),
            'migrated_at': datetime.now()
        }

        if 'timestamp' in p_info and isinstance(p_info['timestamp'], str):
            try:
                doc['timestamp'] = datetime.strptime(p_info['timestamp'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                doc['timestamp'] = p_info['timestamp']

        docs.append(doc)

    if docs:
        payments_col.insert_many(docs)
        print(f"Migrated {len(docs)} payments.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local JSON DB to MongoDB")
    parser.add_argument("--uri", type=str, help="MongoDB URI", default=MONGO_URI)
    args = parser.parse_args()

    if args.uri:
        client = MongoClient(args.uri)
        db = client[DB_NAME]

    print(f"Starting migration to database: {DB_NAME}")
    migrate_users()
    migrate_configs()
    migrate_payments()
    print("Migration complete.")
