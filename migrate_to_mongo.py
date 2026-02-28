import json
import os
import sys
from pymongo import MongoClient
from datetime import datetime

# Configure MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://admin:admin@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.getenv("MONGO_DB_NAME", "vpn_bot_db")

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"Warning: File {filepath} not found.")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON from {filepath}.")
        return {}

def migrate_users(db, users_data):
    users_collection = db['users']
    migrated_count = 0
    for user_id, user_info in users_data.items():
        user_doc = {
            '_id': str(user_id), # Ensure _id is string for easy lookup
            'balance': float(user_info.get('balance', 0)),
            'subscription_end': user_info.get('subscription_end'),
            'referred_by': str(user_info.get('referred_by')) if user_info.get('referred_by') else None,
            'username': user_info.get('username', ''),
            'first_name': user_info.get('first_name', ''),
            'referrals_count': int(user_info.get('referrals_count', 0)),
            'used_configs': user_info.get('used_configs', [])
        }

        # Convert subscription_end to ISODate if it exists and is valid format
        if user_doc['subscription_end']:
            try:
                dt = datetime.strptime(user_doc['subscription_end'], '%Y-%m-%d %H:%M:%S')
                user_doc['subscription_end_date'] = dt
            except ValueError:
                pass # Keep as string if parsing fails, or handle differently

        try:
            users_collection.update_one({'_id': user_doc['_id']}, {'$set': user_doc}, upsert=True)
            migrated_count += 1
        except Exception as e:
            print(f"Error migrating user {user_id}: {e}")
    print(f"Migrated {migrated_count} users.")

def migrate_configs(db, configs_data):
    configs_collection = db['configs']
    migrated_count = 0
    for period, configs_list in configs_data.items():
        for config in configs_list:
            config_doc = {
                'period': period,
                'name': config.get('name'),
                'link': config.get('link'),
                'code': config.get('code'),
                'used': config.get('used', False)
            }
            # Use link as unique identifier if possible, or just insert
            try:
                # Update if link exists, otherwise insert
                if config_doc['link']:
                     configs_collection.update_one({'link': config_doc['link']}, {'$set': config_doc}, upsert=True)
                else:
                     configs_collection.insert_one(config_doc)
                migrated_count += 1
            except Exception as e:
                print(f"Error migrating config {config_doc.get('name')}: {e}")
    print(f"Migrated {migrated_count} configs.")

def migrate_payments(db, payments_data):
    payments_collection = db['payments']
    migrated_count = 0
    for payment_id, payment_info in payments_data.items():
        payment_doc = {
            '_id': str(payment_id),
            'user_id': str(payment_info.get('user_id')),
            'amount': float(payment_info.get('amount', 0)),
            'status': payment_info.get('status'),
            'method': payment_info.get('method'),
            'timestamp': payment_info.get('timestamp'),
            'type': payment_info.get('type')
        }

        # Parse timestamp if valid
        if payment_doc['timestamp']:
             try:
                dt = datetime.strptime(payment_doc['timestamp'], '%Y-%m-%d %H:%M:%S')
                payment_doc['timestamp_date'] = dt
             except ValueError:
                pass

        try:
            payments_collection.update_one({'_id': payment_doc['_id']}, {'$set': payment_doc}, upsert=True)
            migrated_count += 1
        except Exception as e:
            print(f"Error migrating payment {payment_id}: {e}")
    print(f"Migrated {migrated_count} payments.")

def main():
    print(f"Connecting to MongoDB...")
    try:
        client = MongoClient(MONGO_URI)
        # Test connection
        client.admin.command('ping')
        db = client[DB_NAME]
        print("Successfully connected to MongoDB.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

    print("Loading local JSON data...")
    users_data = load_json('users.json')
    configs_data = load_json('configs.json')
    payments_data = load_json('payments.json')

    print("Starting migration...")
    migrate_users(db, users_data)
    migrate_configs(db, configs_data)
    migrate_payments(db, payments_data)
    print("Migration complete.")

if __name__ == "__main__":
    main()
