import json
import os
import sys
from pymongo import MongoClient

# Configuration
MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

def load_json(filename):
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
    print(f"Connecting to MongoDB: {MONGO_URI.split('@')[-1]}") # Hide credentials
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        return

    # 1. Migrate Users
    users_data = load_json('users.json')
    if users_data:
        print(f"Migrating {len(users_data)} users...")
        users_col = db['users']
        ops = []
        for uid, data in users_data.items():
            # Ensure _id is string (Telegram ID)
            data['_id'] = str(uid)

            # Remove old structure artifacts if needed
            # e.g., if 'balance' is string, convert to float?
            # Assuming JSON structure matches what we want mostly.

            # Upsert
            from pymongo import UpdateOne
            ops.append(UpdateOne({'_id': str(uid)}, {'$set': data}, upsert=True))

        if ops:
            result = users_col.bulk_write(ops)
            print(f"Users migrated: {result.upserted_count + result.modified_count}")

    # 2. Migrate Configs
    configs_data = load_json('configs.json')
    if configs_data:
        print("Migrating configs...")
        configs_col = db['configs']
        ops = []
        for period, config_list in configs_data.items():
            for conf in config_list:
                # Add period info to the document itself
                conf['period'] = period
                # Use link as unique identifier or generate one?
                # Using link as key for dedup
                ops.append(UpdateOne({'link': conf['link']}, {'$set': conf}, upsert=True))

        if ops:
            result = configs_col.bulk_write(ops)
            print(f"Configs migrated: {result.upserted_count + result.modified_count}")

    # 3. Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        print(f"Migrating {len(payments_data)} payments...")
        payments_col = db['payments']
        ops = []
        for pid, data in payments_data.items():
            data['_id'] = str(pid)
            ops.append(UpdateOne({'_id': str(pid)}, {'$set': data}, upsert=True))

        if ops:
            result = payments_col.bulk_write(ops)
            print(f"Payments migrated: {result.upserted_count + result.modified_count}")

    print("Migration complete.")

if __name__ == "__main__":
    if "mongodb+srv" not in MONGO_URI and "mongodb://" not in MONGO_URI:
        print("Please set MONGODB_URI environment variable.")
        print("Example: MONGODB_URI='mongodb+srv://user:pass@...' python migrate_to_mongo.py")
    else:
        migrate()
