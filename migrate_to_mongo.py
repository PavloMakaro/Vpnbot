import json
import os
import datetime
from pymongo import MongoClient
import sys

# Configuration
MONGO_URI = "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "vpn_bot"

def load_json(filename):
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found. Skipping.")
        return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error decoding {filename}.")
        return {}

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None

def migrate():
    print("Starting migration...")

    # Check if user provided URI in args
    uri = MONGO_URI
    if len(sys.argv) > 1:
        uri = sys.argv[1]

    if "<username>" in uri:
        print("Please provide a valid MongoDB URI as an argument or edit the script.")
        print("Usage: python migrate_to_mongo.py <mongodb_uri>")
        return

    client = MongoClient(uri)
    db = client[DB_NAME]

    # 1. Migrate Users
    users_data = load_json('users.json')
    if users_data:
        users_coll = db['users']
        bulk_users = []
        for user_id, user_info in users_data.items():
            # Convert used_configs date strings to datetime objects if needed
            cleaned_configs = []
            for conf in user_info.get('used_configs', []):
                # Ensure structure matches what we want
                cleaned_configs.append(conf)

            doc = {
                "_id": str(user_id), # Telegram ID as _id
                "username": user_info.get('username'),
                "first_name": user_info.get('first_name'),
                "balance": float(user_info.get('balance', 0)),
                "subscription_end": parse_date(user_info.get('subscription_end')),
                "referred_by": str(user_info.get('referred_by')) if user_info.get('referred_by') else None,
                "referrals_count": int(user_info.get('referrals_count', 0)),
                "used_configs": cleaned_configs,
                "created_at": datetime.datetime.now() # Fallback since we don't have registration date
            }
            bulk_users.append(doc)

        if bulk_users:
            try:
                users_coll.insert_many(bulk_users)
                print(f"Migrated {len(bulk_users)} users.")
            except Exception as e:
                print(f"Error inserting users: {e}")

    # 2. Migrate Configs
    # In JSON: { "1_month": [ { "name":..., "link":..., "used":... }, ... ] }
    # In Mongo: flat collection with 'period' field
    configs_data = load_json('configs.json')
    if configs_data:
        configs_coll = db['configs']
        bulk_configs = []
        for period, config_list in configs_data.items():
            for conf in config_list:
                doc = {
                    "name": conf.get('name'),
                    "link": conf.get('link'),
                    "code": conf.get('code'),
                    "period": period,
                    "used": conf.get('used', False),
                    # We don't have user_id here easily unless we cross-ref, but 'used' is enough for pool logic
                }
                bulk_configs.append(doc)

        if bulk_configs:
            try:
                configs_coll.insert_many(bulk_configs)
                print(f"Migrated {len(bulk_configs)} configs.")
            except Exception as e:
                print(f"Error inserting configs: {e}")

    # 3. Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        payments_coll = db['payments']
        bulk_payments = []
        for payment_id, p_data in payments_data.items():
            doc = {
                "_id": payment_id,
                "user_id": str(p_data.get('user_id')),
                "amount": float(p_data.get('amount', 0)),
                "status": p_data.get('status'),
                "method": p_data.get('method'),
                "timestamp": parse_date(p_data.get('timestamp')),
                "type": p_data.get('type')
            }
            bulk_payments.append(doc)

        if bulk_payments:
            try:
                payments_coll.insert_many(bulk_payments)
                print(f"Migrated {len(bulk_payments)} payments.")
            except Exception as e:
                print(f"Error inserting payments: {e}")

    print("Migration complete.")

if __name__ == "__main__":
    migrate()
