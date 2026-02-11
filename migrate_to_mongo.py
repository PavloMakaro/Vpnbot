import json
import os
from pymongo import MongoClient
import datetime
import sys

# === CONFIGURATION ===
# Replace with your connection string or use environment variable
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

def load_data(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found. Skipping.")
        return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return {}

def migrate():
    print("Starting migration...")

    # Connect to MongoDB
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        print(f"Connected to MongoDB: {DB_NAME}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        print("Please set the MONGO_URI environment variable correctly.")
        return

    # 1. Migrate Users
    users_data = load_data('users.json')
    if users_data:
        users_col = db['users']
        bulk_users = []
        for user_id, user_info in users_data.items():
            # Convert string ID to int/string as needed. keeping as string for consistency with keys
            user_doc = {
                '_id': user_id,
                'username': user_info.get('username'),
                'first_name': user_info.get('first_name'),
                'balance': user_info.get('balance', 0),
                'subscription_end': None, # Convert to date object
                'referrals_count': user_info.get('referrals_count', 0),
                'referred_by': user_info.get('referred_by'),
                'used_configs': user_info.get('used_configs', [])
            }

            sub_end = user_info.get('subscription_end')
            if sub_end:
                try:
                    user_doc['subscription_end'] = datetime.datetime.strptime(sub_end, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    user_doc['subscription_end'] = None

            bulk_users.append(user_doc)

        if bulk_users:
            try:
                # Use replace_one with upsert to avoid duplicates if running multiple times
                for u in bulk_users:
                    users_col.replace_one({'_id': u['_id']}, u, upsert=True)
                print(f"Migrated {len(bulk_users)} users.")
            except Exception as e:
                print(f"Error migrating users: {e}")

    # 2. Migrate Configs
    configs_data = load_data('configs.json')
    if configs_data:
        configs_col = db['configs']
        bulk_configs = []
        for period, configs_list in configs_data.items():
            for config in configs_list:
                config_doc = {
                    'period': period,
                    'name': config.get('name'),
                    'link': config.get('link'),
                    'code': config.get('code'),
                    'used': config.get('used', False)
                }
                bulk_configs.append(config_doc)

        if bulk_configs:
            try:
                # We don't have unique IDs for configs in the JSON, so we just insert them.
                # To avoid duplicates on re-run, we might want to check existence by link.
                for c in bulk_configs:
                    if not configs_col.find_one({'link': c['link']}):
                        configs_col.insert_one(c)
                print(f"Migrated {len(bulk_configs)} configs.")
            except Exception as e:
                print(f"Error migrating configs: {e}")

    # 3. Migrate Payments
    payments_data = load_data('payments.json')
    if payments_data:
        payments_col = db['payments']
        bulk_payments = []
        for payment_id, payment_info in payments_data.items():
            payment_doc = {
                '_id': payment_id,
                'user_id': payment_info.get('user_id'),
                'amount': payment_info.get('amount'),
                'status': payment_info.get('status'),
                'method': payment_info.get('method'),
                'timestamp': None,
                'type': payment_info.get('type'),
                'payment_id_yookassa': payment_info.get('payment_id') # Renamed to avoid conflict with _id
            }

            ts = payment_info.get('timestamp')
            if ts:
                try:
                    payment_doc['timestamp'] = datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    payment_doc['timestamp'] = None

            bulk_payments.append(payment_doc)

        if bulk_payments:
            try:
                for p in bulk_payments:
                    payments_col.replace_one({'_id': p['_id']}, p, upsert=True)
                print(f"Migrated {len(bulk_payments)} payments.")
            except Exception as e:
                print(f"Error migrating payments: {e}")

    # 4. Create Plans (Static)
    plans_col = db['plans']
    SUBSCRIPTION_PERIODS = {
        '1_month': {'price': 50, 'days': 30},
        '2_months': {'price': 90, 'days': 60},
        '3_months': {'price': 120, 'days': 90}
    }

    for plan_id, plan_data in SUBSCRIPTION_PERIODS.items():
        plan_doc = {
            '_id': plan_id,
            'days': plan_data['days'],
            'price': plan_data['price']
        }
        try:
            plans_col.replace_one({'_id': plan_id}, plan_doc, upsert=True)
        except Exception as e:
            print(f"Error creating plan {plan_id}: {e}")
    print("Plans collection updated.")

    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
