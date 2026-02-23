import json
import os
import datetime
import sys
from pymongo import MongoClient

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None

def migrate_users(db):
    if not os.path.exists('users.json'):
        print("users.json not found, skipping.")
        return

    with open('users.json', 'r', encoding='utf-8') as f:
        try:
            users_data = json.load(f)
        except json.JSONDecodeError:
            print("users.json is empty or invalid.")
            return

    collection = db['users']
    count = 0
    for uid, data in users_data.items():
        doc = {
            '_id': uid,
            'balance': data.get('balance', 0),
            'subscription_end': parse_date(data.get('subscription_end')),
            'username': data.get('username'),
            'first_name': data.get('first_name'),
            'referrals_count': data.get('referrals_count', 0),
            'referred_by': data.get('referred_by'),
            'joined_at': datetime.datetime.now() # Approximate
        }

        # Process used_configs if needed
        used_configs = data.get('used_configs', [])
        # We store them as is, but maybe parse issue_date string?
        # In JS we treat them as strings or dates. Best to parse.
        # But JSON stores strings.

        doc['used_configs'] = used_configs

        try:
            collection.replace_one({'_id': uid}, doc, upsert=True)
            count += 1
        except Exception as e:
            print(f"Error migrating user {uid}: {e}")

    print(f"Migrated {count} users.")

def migrate_configs(db):
    if not os.path.exists('configs.json'):
        print("configs.json not found, skipping.")
        return

    with open('configs.json', 'r', encoding='utf-8') as f:
        try:
            configs_data = json.load(f)
        except json.JSONDecodeError:
            print("configs.json is empty or invalid.")
            return

    collection = db['configs']
    count = 0

    # Structure: {'1_month': [ {name, link, code, used}, ... ]}
    for period, configs_list in configs_data.items():
        for config in configs_list:
            doc = {
                'period': period,
                'name': config.get('name'),
                'link': config.get('link'),
                'code': config.get('code'),
                'used': config.get('used', False)
            }
            try:
                # Use link as unique key to prevent duplicates
                collection.update_one(
                    {'link': doc['link']},
                    {'$set': doc},
                    upsert=True
                )
                count += 1
            except Exception as e:
                print(f"Error migrating config {config.get('name')}: {e}")

    print(f"Migrated {count} configs.")

def migrate_payments(db):
    if not os.path.exists('payments.json'):
        print("payments.json not found, skipping.")
        return

    with open('payments.json', 'r', encoding='utf-8') as f:
        try:
            payments_data = json.load(f)
        except json.JSONDecodeError:
            print("payments.json is empty or invalid.")
            return

    collection = db['payments']
    count = 0
    for pid, data in payments_data.items():
        doc = {
            '_id': pid,
            'user_id': data.get('user_id'),
            'amount': data.get('amount'),
            'status': data.get('status'),
            'method': data.get('method'),
            'timestamp': parse_date(data.get('timestamp')),
            'type': data.get('type')
        }
        try:
            collection.replace_one({'_id': pid}, doc, upsert=True)
            count += 1
        except Exception as e:
            print(f"Error migrating payment {pid}: {e}")

    print(f"Migrated {count} payments.")

if __name__ == "__main__":
    if not MONGO_URI:
        print("ERROR: Please set MONGO_URI environment variable.")
        print("Example: export MONGO_URI='mongodb+srv://user:pass@cluster.mongodb.net'")
        sys.exit(1)

    client = MongoClient(MONGO_URI)
    db = client['vpn_bot']

    print("Starting migration...")
    migrate_users(db)
    migrate_configs(db)
    migrate_payments(db)
    print("Migration complete.")
