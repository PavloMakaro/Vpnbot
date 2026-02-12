import json
import os
import sys
from pymongo import MongoClient

# Instructions:
# 1. Install pymongo: pip install pymongo
# 2. Set MONGODB_URI environment variable or edit the string below
# 3. Run: python scripts/migrate_to_mongo.py

CONNECTION_STRING = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/vpn_bot")

def load_json(filename):
    # Check current directory and parent directory for data files
    paths = [filename, os.path.join('..', filename)]
    for path in paths:
        if os.path.exists(path):
            print(f"Found {filename} at {path}")
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    print(f"Warning: {filename} not found.")
    return {}

def migrate():
    try:
        client = MongoClient(CONNECTION_STRING)
        db = client.get_database("vpn_bot")
        print(f"Connected to MongoDB: {db.name}")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return

    # Migrate Users
    users_data = load_json('users.json')
    if users_data:
        users_list = []
        for uid, data in users_data.items():
            # Convert user ID to string just in case, use as _id
            data['_id'] = str(uid)
            # Ensure used_configs is a list
            if 'used_configs' not in data:
                data['used_configs'] = []
            users_list.append(data)

        if users_list:
            try:
                # Use bulk_write or insert_many with ordered=False to skip duplicates
                db.users.insert_many(users_list, ordered=False)
                print(f"Migrated {len(users_list)} users.")
            except Exception as e:
                print(f"Error inserting users (some might be duplicates): {e}")

    # Migrate Configs
    configs_data = load_json('configs.json')
    if configs_data:
        configs_list = []
        for period, configs in configs_data.items():
            for conf in configs:
                conf['period'] = period
                # Ensure fields exist
                if 'used' not in conf:
                    conf['used'] = False
                configs_list.append(conf)

        if configs_list:
            try:
                db.configs.insert_many(configs_list, ordered=False)
                print(f"Migrated {len(configs_list)} configs.")
            except Exception as e:
                print(f"Error inserting configs: {e}")

    # Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        payments_list = []
        for pid, data in payments_data.items():
            data['payment_id'] = pid
            # Let Mongo generate _id or use pid
            payments_list.append(data)

        if payments_list:
            try:
                db.payments.insert_many(payments_list, ordered=False)
                print(f"Migrated {len(payments_list)} payments.")
            except Exception as e:
                print(f"Error inserting payments: {e}")

    # Create Plans Collection (Hardcoded based on code)
    plans = [
        {'_id': '1_month', 'price': 50, 'days': 30, 'name': '1 Month'},
        {'_id': '2_months', 'price': 90, 'days': 60, 'name': '2 Months'},
        {'_id': '3_months', 'price': 120, 'days': 90, 'name': '3 Months'}
    ]
    try:
        db.plans.insert_many(plans, ordered=False)
        print("Initialized plans collection.")
    except Exception as e:
        pass # Likely duplicates

if __name__ == "__main__":
    migrate()
