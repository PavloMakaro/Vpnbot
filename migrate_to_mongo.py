import json
import os
import pymongo
from pymongo import MongoClient

# Configure MongoDB Connection
# Set env var MONGODB_URI or edit this line
MONGO_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority')
DB_NAME = 'vpn_bot'

def load_json(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found, skipping.")
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def migrate():
    print(f"Connecting to MongoDB: {MONGO_URI}")
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        print("Connected successfully.")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # 1. Migrate Users
    users_data = load_json('users.json')
    if users_data:
        users_col = db['users']
        print(f"Migrating {len(users_data)} users...")
        for user_id, user_info in users_data.items():
            user_info['_id'] = user_id  # Use user_id as _id
            try:
                users_col.replace_one({'_id': user_id}, user_info, upsert=True)
            except Exception as e:
                print(f"Error upserting user {user_id}: {e}")
        print("Users migration complete.")

    # 2. Migrate Configs
    configs_data = load_json('configs.json')
    if configs_data:
        configs_col = db['configs']
        print("Migrating configs...")
        count = 0
        for period, configs_list in configs_data.items():
            for config in configs_list:
                # Add period to config object
                config['period'] = period
                # Generate an _id if not present based on link or code to avoid dupes
                # Assuming 'link' is unique enough or 'code'
                unique_key = config.get('link') or config.get('code')
                if not unique_key:
                    print(f"Skipping config without link/code: {config}")
                    continue

                query = {'link': config.get('link')} if config.get('link') else {'code': config.get('code')}

                try:
                    configs_col.update_one(query, {'$set': config}, upsert=True)
                    count += 1
                except Exception as e:
                    print(f"Error upserting config: {e}")
        print(f"Migrated {count} configs.")

    # 3. Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        payments_col = db['payments']
        print(f"Migrating {len(payments_data)} payments...")
        for payment_id, payment_info in payments_data.items():
            payment_info['_id'] = payment_id
            try:
                payments_col.replace_one({'_id': payment_id}, payment_info, upsert=True)
            except Exception as e:
                print(f"Error upserting payment {payment_id}: {e}")
        print("Payments migration complete.")

if __name__ == "__main__":
    migrate()
