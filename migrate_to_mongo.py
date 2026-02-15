import json
import os
import sys
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "vpn_bot"

def load_json(filename):
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found.")
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def migrate():
    if not MONGO_URI:
        print("Error: MONGO_URI environment variable not set.")
        print("Usage: MONGO_URI='mongodb+srv://...' python migrate_to_mongo.py")
        sys.exit(1)

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # Migrate Users
    users_data = load_json('users.json')
    if users_data:
        users_coll = db['users']
        bulk_users = []
        for uid, udata in users_data.items():
            # Convert dates
            sub_end = udata.get('subscription_end')
            if sub_end:
                try:
                    udata['subscription_end'] = datetime.strptime(sub_end, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    udata['subscription_end'] = None

            udata['_id'] = str(uid)

            # Handle used_configs (if any) to match new schema logic if needed
            # But we'll keep them as embedded for history or reference

            bulk_users.append(udata)

        if bulk_users:
            try:
                users_coll.insert_many(bulk_users, ordered=False)
                print(f"Migrated {len(bulk_users)} users.")
            except Exception as e:
                print(f"Error inserting users (some might verify exist): {e}")

    # Migrate Configs
    configs_data = load_json('configs.json')
    if configs_data:
        configs_coll = db['configs']
        bulk_configs = []
        for period, config_list in configs_data.items():
            for conf in config_list:
                conf['period'] = period
                # Ensure 'used' is boolean
                conf['used'] = conf.get('used', False)
                bulk_configs.append(conf)

        if bulk_configs:
            try:
                configs_coll.insert_many(bulk_configs, ordered=False)
                print(f"Migrated {len(bulk_configs)} configs.")
            except Exception as e:
                print(f"Error inserting configs: {e}")

    # Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        payments_coll = db['payments']
        bulk_payments = []
        for pid, pdata in payments_data.items():
            pdata['_id'] = str(pid)
            ts = pdata.get('timestamp')
            if ts:
                try:
                    pdata['created_at'] = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pdata['created_at'] = datetime.now()

            bulk_payments.append(pdata)

        if bulk_payments:
            try:
                payments_coll.insert_many(bulk_payments, ordered=False)
                print(f"Migrated {len(bulk_payments)} payments.")
            except Exception as e:
                print(f"Error inserting payments: {e}")

    print("Migration complete.")

if __name__ == "__main__":
    migrate()
