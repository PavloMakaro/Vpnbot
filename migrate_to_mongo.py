import json
import os
import datetime
from pymongo import MongoClient

def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Skipping.")
        return {}

def migrate():
    MONGO_URI = os.getenv("MONGO_URI")
    if not MONGO_URI:
        print("Error: MONGO_URI environment variable not set.")
        print("Please export MONGO_URI='mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority'")
        return

    try:
        client = MongoClient(MONGO_URI)
        db = client["vpn_bot"] # Database name
        print(f"Connected to MongoDB: {db.name}")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return

    # 1. Migrate Users
    users_db = load_data('users.json')
    if users_db:
        users_collection = db["users"]
        print(f"Migrating {len(users_db)} users...")
        for user_id, user_data in users_db.items():
            # Adjust structure
            doc = user_data.copy()
            doc['_id'] = str(user_id) # Ensure ID is string

            # Convert dates
            if 'subscription_end' in doc and doc['subscription_end']:
                try:
                    doc['subscription_end'] = datetime.datetime.strptime(doc['subscription_end'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # Try fallback or leave as string/null
                    pass

            # Upsert
            try:
                users_collection.replace_one({'_id': doc['_id']}, doc, upsert=True)
            except Exception as e:
                print(f"Error inserting user {user_id}: {e}")
        print("Users migrated.")

    # 2. Migrate Configs
    configs_db = load_data('configs.json')
    if configs_db:
        configs_collection = db["configs"]
        print("Migrating configs...")
        count = 0
        for period, configs_list in configs_db.items():
            for config in configs_list:
                doc = config.copy()
                doc['period'] = period

                # Config link is usually unique.
                if 'link' in doc:
                    try:
                        configs_collection.replace_one({'link': doc['link']}, doc, upsert=True)
                        count += 1
                    except Exception as e:
                        print(f"Error inserting config {doc.get('name')}: {e}")
        print(f"Migrated {count} configs.")

    # 3. Migrate Payments
    payments_db = load_data('payments.json')
    if payments_db:
        payments_collection = db["payments"]
        print(f"Migrating {len(payments_db)} payments...")
        for payment_id, payment_data in payments_db.items():
            doc = payment_data.copy()
            doc['_id'] = str(payment_id)
             # Convert dates
            if 'timestamp' in doc:
                 try:
                    doc['created_at'] = datetime.datetime.strptime(doc['timestamp'], '%Y-%m-%d %H:%M:%S')
                 except:
                    pass

            try:
                payments_collection.replace_one({'_id': doc['_id']}, doc, upsert=True)
            except Exception as e:
                print(f"Error inserting payment {payment_id}: {e}")
        print("Payments migrated.")

    print("Migration complete.")

if __name__ == "__main__":
    migrate()
