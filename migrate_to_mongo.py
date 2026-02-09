import json
import os
from pymongo import MongoClient

# Placeholder - replace with actual connection string
MONGO_URI = "mongodb+srv://<username>:<password>@cluster0.mongodb.net/test"
DB_NAME = "vpn_bot"

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding {filename}")
            return {}
    else:
        print(f"File {filename} not found.")
        return {}

def migrate():
    try:
        # Note: This will fail if pymongo is not installed or URI is invalid
        # But this is a migration script intended to be run manually once setup is complete
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # 1. Migrate Users
        users_data = load_json('users.json')
        if users_data:
            print(f"Migrating {len(users_data)} users...")
            users_collection = db['users']
            users_list = []
            for user_id, user_info in users_data.items():
                user_doc = user_info.copy()
                user_doc['_id'] = str(user_id) # Ensure ID is string as in JSON
                users_list.append(user_doc)

            if users_list:
                try:
                    # Use ordered=False to continue inserting if some fail (e.g. duplicates)
                    result = users_collection.insert_many(users_list, ordered=False)
                    print(f"Inserted {len(result.inserted_ids)} users.")
                except Exception as e:
                    print(f"Partial error inserting users (might be duplicates): {e}")
        else:
            print("No users.json found or empty.")

        # 2. Migrate Configs
        configs_data = load_json('configs.json')
        if configs_data:
            print(f"Migrating configs...")
            configs_collection = db['configs']
            configs_list = []
            for period, configs in configs_data.items():
                for config in configs:
                    config_doc = config.copy()
                    config_doc['period'] = period
                    # If config doesn't have a unique ID, MongoDB will generate one
                    configs_list.append(config_doc)

            if configs_list:
                try:
                    result = configs_collection.insert_many(configs_list, ordered=False)
                    print(f"Inserted {len(result.inserted_ids)} configs.")
                except Exception as e:
                    print(f"Error inserting configs: {e}")
        else:
            print("No configs.json found or empty.")

        # 3. Migrate Payments
        payments_data = load_json('payments.json')
        if payments_data:
            print(f"Migrating {len(payments_data)} payments...")
            payments_collection = db['payments']
            payments_list = []
            for payment_id, payment_info in payments_data.items():
                payment_doc = payment_info.copy()
                payment_doc['_id'] = payment_id
                payments_list.append(payment_doc)

            if payments_list:
                try:
                    result = payments_collection.insert_many(payments_list, ordered=False)
                    print(f"Inserted {len(result.inserted_ids)} payments.")
                except Exception as e:
                    print(f"Error inserting payments: {e}")
        else:
            print("No payments.json found or empty.")

        print("Migration completed.")

    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
