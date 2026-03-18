import json
import os
import pymongo
from pymongo import MongoClient

# Allow overriding client for testing (mock)
client = None

def get_client():
    global client
    if client is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        client = MongoClient(mongo_uri)
    return client

def load_json_data(filepath):
    """Load data from a JSON file. Return empty dict if not found."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File {filepath} not found. Skipping.")
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {filepath}. Skipping.")
        return {}

def migrate_data():
    """Migrate data from legacy JSON files to MongoDB vpn_bot database."""
    db_client = get_client()
    db = db_client['vpn_bot']

    users_db = load_json_data('users.json')
    configs_db = load_json_data('configs.json')
    payments_db = load_json_data('payments.json')

    users_col = db['users']
    configs_col = db['configs']
    payments_col = db['payments']

    # Migrate users
    print("Migrating users...")
    user_docs = []
    for user_id, user_data in users_db.items():
        doc = dict(user_data)
        doc['_id'] = str(user_id)  # Use string Telegram ID as _id
        user_docs.append(doc)

    if user_docs:
        try:
            # Upsert users
            for doc in user_docs:
                users_col.replace_one({'_id': doc['_id']}, doc, upsert=True)
            print(f"Migrated {len(user_docs)} users.")
        except Exception as e:
            print(f"Error migrating users: {e}")
    else:
        print("No users to migrate.")

    # Migrate configs
    print("Migrating configs...")
    config_docs = []
    for period, config_list in configs_db.items():
        for config_data in config_list:
            doc = dict(config_data)
            doc['period'] = period
            if 'used' not in doc:
                doc['used'] = False
            config_docs.append(doc)

    if config_docs:
        try:
            configs_col.insert_many(config_docs)
            print(f"Migrated {len(config_docs)} configs.")
        except Exception as e:
            print(f"Error migrating configs: {e}")
    else:
        print("No configs to migrate.")

    # Migrate payments
    print("Migrating payments...")
    payment_docs = []
    for payment_id, payment_data in payments_db.items():
        doc = dict(payment_data)
        doc['_id'] = payment_id # Keep payment ID as primary key
        payment_docs.append(doc)

    if payment_docs:
        try:
            for doc in payment_docs:
                payments_col.replace_one({'_id': doc['_id']}, doc, upsert=True)
            print(f"Migrated {len(payment_docs)} payments.")
        except Exception as e:
            print(f"Error migrating payments: {e}")
    else:
        print("No payments to migrate.")

    print("Migration complete.")

if __name__ == "__main__":
    migrate_data()
