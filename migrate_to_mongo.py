import json
import os
from pymongo import MongoClient

# Initialize mongo client directly for easier injection
client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017'))

def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def migrate_data():
    db = client['vpn_bot']

    # Migrating Users
    users_data = load_data('users.json')
    if users_data:
        users_col = db['users']
        bulk_users = []
        for uid, info in users_data.items():
            # Explicit string cast
            info['telegram_id'] = str(uid)
            info['balance'] = float(info.get('balance', 0))
            # Insert or replace
            users_col.update_one({'telegram_id': info['telegram_id']}, {'$set': info}, upsert=True)
        print(f"Migrated {len(users_data)} users.")

    # Migrating Configs
    configs_data = load_data('configs.json')
    if configs_data:
        configs_col = db['configs']
        count = 0
        for period, config_list in configs_data.items():
            for conf in config_list:
                conf['period'] = period
                if '_id' in conf:
                   del conf['_id'] # Let mongo generate unique _id
                # Only insert if link doesn't exist
                configs_col.update_one({'link': conf['link']}, {'$set': conf}, upsert=True)
                count += 1
        print(f"Migrated {count} configs.")

    # Migrating Payments
    payments_data = load_data('payments.json')
    if payments_data:
        payments_col = db['payments']
        for pid, pdata in payments_data.items():
            pdata['_id'] = str(pid)
            pdata['user_id'] = str(pdata.get('user_id', ''))
            payments_col.update_one({'_id': str(pid)}, {'$set': pdata}, upsert=True)
        print(f"Migrated {len(payments_data)} payments.")

if __name__ == "__main__":
    migrate_data()