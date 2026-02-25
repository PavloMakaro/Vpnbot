import json
import os
import pymongo
from datetime import datetime

# Load environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://user:pass@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

def load_json(filename):
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found, skipping.")
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def migrate():
    print(f"Connecting to MongoDB: {MONGO_URI}")
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # 1. Migrate Users
    users_data = load_json('users.json')
    if users_data:
        print(f"Migrating {len(users_data)} users...")
        users_col = db['users']

        operations = []
        for user_id, user in users_data.items():
            # Convert user_id to string explicitly just in case
            uid = str(user_id)

            # Prepare user document
            doc = {
                "_id": uid,
                "username": user.get("username"),
                "first_name": user.get("first_name"),
                "balance": user.get("balance", 0),
                "subscription_end": user.get("subscription_end"), # Keep as string or convert to Date?
                                                                 # Ideally convert to Date, but backend handles string parsing too.
                                                                 # Let's convert to Date if possible.
                "referrals_count": user.get("referrals_count", 0),
                "referred_by": user.get("referred_by"),
                "used_configs": user.get("used_configs", [])
            }

            # Convert dates
            if doc["subscription_end"]:
                try:
                    doc["subscription_end"] = datetime.strptime(doc["subscription_end"], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass # Keep as string if format differs

            operations.append(pymongo.UpdateOne({"_id": uid}, {"$set": doc}, upsert=True))

        if operations:
            result = users_col.bulk_write(operations)
            print(f"Users migrated: {result.upserted_count} upserted, {result.modified_count} modified.")

    # 2. Migrate Configs
    configs_data = load_json('configs.json')
    if configs_data:
        print("Migrating configs...")
        configs_col = db['configs']

        operations = []
        count = 0
        for period, configs_list in configs_data.items():
            for config in configs_list:
                # Flatten structure
                doc = {
                    "period": period,
                    "name": config.get("name"),
                    "link": config.get("link"),
                    "code": config.get("code"),
                    "used": config.get("used", False)
                }

                # Identify config uniquely? Maybe by link.
                filter_query = {"link": doc["link"]}
                operations.append(pymongo.UpdateOne(filter_query, {"$set": doc}, upsert=True))
                count += 1

        if operations:
            result = configs_col.bulk_write(operations)
            print(f"Configs migrated: {result.upserted_count} upserted, {result.modified_count} modified (Total: {count}).")

    # 3. Migrate Payments
    payments_data = load_json('payments.json')
    if payments_data:
        print(f"Migrating {len(payments_data)} payments...")
        payments_col = db['payments']

        operations = []
        for payment_id, payment in payments_data.items():
            doc = {
                "_id": payment_id,
                "user_id": str(payment.get("user_id")),
                "amount": payment.get("amount"),
                "status": payment.get("status"),
                "method": payment.get("method"),
                "timestamp": payment.get("timestamp"), # Convert to Date if needed
                "type": payment.get("type"),
                "yookassa_id": payment.get("payment_id") # Note: original json keys might differ
            }

            # Handle payment_id field conflict (payment_id in json is yookassa id, key is internal id)
            # In original code: payments_db[payment.id] = { ... 'payment_id': payment.id }

            operations.append(pymongo.UpdateOne({"_id": payment_id}, {"$set": doc}, upsert=True))

        if operations:
            result = payments_col.bulk_write(operations)
            print(f"Payments migrated: {result.upserted_count} upserted, {result.modified_count} modified.")

    print("Migration complete.")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"Migration failed: {e}")
