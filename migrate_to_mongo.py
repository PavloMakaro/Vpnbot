import json
import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Let client be overridable for testing
client = None

def get_mongo_client():
    global client
    if client is not None:
        return client

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI environment variable must be set")
    client = MongoClient(mongo_uri)
    return client

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"File {filepath} not found. Skipping.")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {filepath}. Skipping.")
        return {}

def migrate_users(db, users_data):
    if not users_data:
        return

    users_coll = db.users
    bulk_ops = []

    for user_id, data in users_data.items():
        doc = {
            "_id": user_id,
            "balance": float(data.get("balance", 0)),
            "subscription_end": data.get("subscription_end"),
            "referred_by": data.get("referred_by"),
            "username": data.get("username"),
            "first_name": data.get("first_name"),
            "referrals_count": int(data.get("referrals_count", 0)),
            "used_configs": data.get("used_configs", [])
        }

        from pymongo import UpdateOne
        bulk_ops.append(UpdateOne({"_id": user_id}, {"$set": doc}, upsert=True))

    if bulk_ops:
        result = users_coll.bulk_write(bulk_ops)
        logging.info(f"Users migration: {result.upserted_count} upserted, {result.modified_count} modified.")

def migrate_configs(db, configs_data):
    if not configs_data:
        return

    configs_coll = db.configs
    bulk_ops = []

    for period, configs in configs_data.items():
        for config in configs:
            doc = {
                "name": config.get("name"),
                "link": config.get("link"),
                "code": config.get("code"),
                "used": bool(config.get("used", False)),
                "period": period
            }

            # Using link as unique identifier to prevent duplicates
            link = config.get("link")
            if link:
                from pymongo import UpdateOne
                bulk_ops.append(UpdateOne({"link": link}, {"$set": doc}, upsert=True))

    if bulk_ops:
        result = configs_coll.bulk_write(bulk_ops)
        logging.info(f"Configs migration: {result.upserted_count} upserted, {result.modified_count} modified.")

def migrate_payments(db, payments_data):
    if not payments_data:
        return

    payments_coll = db.payments
    bulk_ops = []

    for payment_id, data in payments_data.items():
        doc = {
            "_id": payment_id,
            "user_id": data.get("user_id"),
            "amount": float(data.get("amount", 0)),
            "status": data.get("status"),
            "method": data.get("method"),
            "timestamp": data.get("timestamp"),
            "type": data.get("type")
        }

        from pymongo import UpdateOne
        bulk_ops.append(UpdateOne({"_id": payment_id}, {"$set": doc}, upsert=True))

    if bulk_ops:
        result = payments_coll.bulk_write(bulk_ops)
        logging.info(f"Payments migration: {result.upserted_count} upserted, {result.modified_count} modified.")

def main():
    try:
        mongo_client = get_mongo_client()
        # Ping the server to check connection
        mongo_client.admin.command('ping')
        logging.info("Connected to MongoDB successfully.")

        db = mongo_client["vpn_bot"]

        users_file = os.getenv("USERS_JSON_PATH", "users.json")
        configs_file = os.getenv("CONFIGS_JSON_PATH", "configs.json")
        payments_file = os.getenv("PAYMENTS_JSON_PATH", "payments.json")

        users_data = load_json(users_file)
        migrate_users(db, users_data)

        configs_data = load_json(configs_file)
        migrate_configs(db, configs_data)

        payments_data = load_json(payments_file)
        migrate_payments(db, payments_data)

        logging.info("Migration completed successfully.")

    except ConnectionFailure:
        logging.error("Failed to connect to MongoDB. Check MONGO_URI.")
    except OperationFailure as e:
        logging.error(f"MongoDB operation failed: {e}")
    except ValueError as e:
        logging.error(str(e))
    except Exception as e:
        logging.error(f"Unexpected error during migration: {e}")
    finally:
        if client is not None and getattr(client, "close", None):
            client.close()

if __name__ == "__main__":
    main()