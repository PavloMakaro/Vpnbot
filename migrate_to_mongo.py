import json
import os
import sys
from pymongo import MongoClient
import datetime

# This will be overridden in tests via mongomock
client = None

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: {filepath} contains invalid JSON.")
        return {}

def migrate():
    global client
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    if not client:
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            sys.exit(1)

    db = client.vpn_bot

    users_db = load_json('users.json')
    configs_db = load_json('configs.json')
    payments_db = load_json('payments.json')

    # Users Migration
    users_coll = db.users
    user_count = 0
    for uid, udata in users_db.items():
        doc = {
            '_id': str(uid),
            'balance': udata.get('balance', 0),
            'username': udata.get('username'),
            'first_name': udata.get('first_name'),
            'referrals_count': udata.get('referrals_count', 0),
            'referred_by': udata.get('referred_by'),
            'used_configs': udata.get('used_configs', []),
            'subscription_end': None,
            'migrated_at': datetime.datetime.now()
        }

        # Parse dates to ISODate if possible
        sub_end = udata.get('subscription_end')
        if sub_end:
            try:
                doc['subscription_end'] = datetime.datetime.strptime(sub_end, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass

        users_coll.update_one({'_id': str(uid)}, {'$set': doc}, upsert=True)
        user_count += 1

    print(f"Migrated {user_count} users.")

    # Configs Migration
    configs_coll = db.configs
    config_count = 0
    for period, clist in configs_db.items():
        for cfg in clist:
            doc = {
                'name': cfg.get('name'),
                'link': cfg.get('link'),
                'code': cfg.get('code'),
                'used': cfg.get('used', False),
                'period': period,
                'migrated_at': datetime.datetime.now()
            }
            # Link is likely unique, use it for matching or generate hash
            configs_coll.update_one({'link': cfg.get('link')}, {'$set': doc}, upsert=True)
            config_count += 1

    print(f"Migrated {config_count} configs.")

    # Payments Migration
    payments_coll = db.payments
    payment_count = 0
    for pid, pdata in payments_db.items():
        doc = {
            '_id': str(pid),
            'user_id': pdata.get('user_id'),
            'amount': pdata.get('amount'),
            'status': pdata.get('status'),
            'method': pdata.get('method'),
            'type': pdata.get('type'),
            'payment_id': pdata.get('payment_id'),
            'period': pdata.get('period'),
            'screenshot_id': pdata.get('screenshot_id'),
            'migrated_at': datetime.datetime.now()
        }

        ts = pdata.get('timestamp')
        if ts:
             try:
                 doc['timestamp'] = datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
             except ValueError:
                 doc['timestamp'] = ts

        payments_coll.update_one({'_id': str(pid)}, {'$set': doc}, upsert=True)
        payment_count += 1

    print(f"Migrated {payment_count} payments.")
    print("Migration complete!")

if __name__ == "__main__":
    migrate()