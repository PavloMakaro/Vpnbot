import json
import os
import pymongo
from datetime import datetime

# MongoDB Connection String (Replace with your actual string)
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def migrate():
    print("Connecting to MongoDB...")
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DB_NAME]
        print(f"Connected to database: {DB_NAME}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        return

    # Migrate Users
    users_data = load_json('users.json')
    if users_data:
        print(f"Migrating {len(users_data)} users...")
        users_col = db['users']
        bulk_ops = []
        for user_id, user_info in users_data.items():
            # Convert date strings to datetime objects if needed, or keep as strings depending on schema
            # Stitch functions expect date objects usually for comparison, but our logic handles strings too.
            # Let's try to convert subscription_end to ISO date if possible.
            sub_end = user_info.get('subscription_end')
            if sub_end:
                try:
                    sub_end = datetime.strptime(sub_end, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass # Keep as string or None

            user_doc = {
                'user_id': str(user_id),
                'balance': user_info.get('balance', 0),
                'subscription_end': sub_end,
                'username': user_info.get('username'),
                'first_name': user_info.get('first_name'),
                'referrals_count': user_info.get('referrals_count', 0),
                'referred_by': user_info.get('referred_by'),
                'used_configs': user_info.get('used_configs', [])
            }
            bulk_ops.append(pymongo.UpdateOne(
                {'user_id': str(user_id)},
                {'$set': user_doc},
                upsert=True
            ))

        if bulk_ops:
            result = users_col.bulk_write(bulk_ops)
            print(f"Users migrated: {result.upserted_count} inserted, {result.modified_count} updated.")

    # Migrate Configs
    configs_data = load_json('configs.json')
    if configs_data:
        print("Migrating configs...")
        configs_col = db['configs']
        bulk_ops = []
        total_configs = 0
        for period, configs_list in configs_data.items():
            for config in configs_list:
                total_configs += 1
                config_doc = {
                    'period': period,
                    'name': config.get('name'),
                    'link': config.get('link'),
                    'code': config.get('code'),
                    'used': config.get('used', False)
                }
                # Use link as unique identifier
                bulk_ops.append(pymongo.UpdateOne(
                    {'link': config.get('link')},
                    {'$set': config_doc},
                    upsert=True
                ))

        if bulk_ops:
            result = configs_col.bulk_write(bulk_ops)
            print(f"Configs migrated: {result.upserted_count} inserted, {result.modified_count} updated.")

    # Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        print(f"Migrating {len(payments_data)} payments...")
        payments_col = db['payments']
        bulk_ops = []
        for payment_id, payment_info in payments_data.items():
            payment_doc = {
                'payment_id': payment_id, # or use inner payment_id if available
                'user_id': str(payment_info.get('user_id')),
                'amount': payment_info.get('amount'),
                'status': payment_info.get('status'),
                'method': payment_info.get('method'),
                'timestamp': payment_info.get('timestamp'),
                'type': payment_info.get('type')
            }
            # Using outer key as ID
            bulk_ops.append(pymongo.UpdateOne(
                {'payment_id': payment_id},
                {'$set': payment_doc},
                upsert=True
            ))

        if bulk_ops:
            result = payments_col.bulk_write(bulk_ops)
            print(f"Payments migrated: {result.upserted_count} inserted, {result.modified_count} updated.")

    print("Migration complete!")

if __name__ == "__main__":
    if "mongodb+srv" in MONGO_URI and "<username>" in MONGO_URI:
        print("Please set the MONGO_URI environment variable or edit the script with your connection string.")
    else:
        migrate()
