import os
import sys
import json
import logging
import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get MongoDB connection string from environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "vpn_bot"

client = None

def get_client():
    global client
    if client is None:
        try:
            client = MongoClient(MONGO_URI)
            # Test connection
            client.admin.command('ping')
        except ConnectionFailure as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            sys.exit(1)
    return client

def safe_load_json(filepath):
    """
    Consolidates OS metadata checks to minimize overhead.
    Attempts to read the file, handling FileNotFoundError and JSONDecodeError.
    """
    try:
        # Instead of multiple os.path calls, just try to open it
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"File not found: {filepath}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON from {filepath}: {e}")
        return {}
    except OSError as e:
        logging.error(f"OS error reading {filepath}: {e}")
        return {}

def migrate_users(db, users_data):
    if not users_data:
        logging.info("No user data to migrate.")
        return

    users_col = db.users
    bulk_ops = []

    for user_id_str, user_info in users_data.items():
        try:
            user_id = int(user_id_str)
        except ValueError:
            user_id = user_id_str

        doc = {
            "telegram_id": user_id,
            "balance": user_info.get("balance", 0),
            "subscription_end": user_info.get("subscription_end"),
            "referred_by": user_info.get("referred_by"),
            "username": user_info.get("username"),
            "first_name": user_info.get("first_name"),
            "referrals_count": user_info.get("referrals_count", 0),
            "used_configs": user_info.get("used_configs", [])
        }
        bulk_ops.append(doc)

    if bulk_ops:
        # Clear existing collection (optional, uncomment if needed)
        # users_col.delete_many({})

        # We can use upsert or just insert if we assume clean slate. Let's do an insert or replace.
        # But for simple migration, replace or insert many.
        for op in bulk_ops:
            users_col.replace_one({"telegram_id": op["telegram_id"]}, op, upsert=True)
        logging.info(f"Migrated {len(bulk_ops)} users.")

def migrate_configs(db, configs_data):
    if not configs_data:
        logging.info("No config data to migrate.")
        return

    configs_col = db.configs
    bulk_ops = []

    for period, config_list in configs_data.items():
        for config in config_list:
            doc = {
                "name": config.get("name"),
                "link": config.get("link"),
                "code": config.get("code"),
                "used": config.get("used", False),
                "period": period
            }
            bulk_ops.append(doc)

    if bulk_ops:
        # Use link as unique key to upsert
        for op in bulk_ops:
            configs_col.replace_one({"link": op["link"]}, op, upsert=True)
        logging.info(f"Migrated {len(bulk_ops)} configs.")

def migrate_payments(db, payments_data):
    if not payments_data:
        logging.info("No payment data to migrate.")
        return

    payments_col = db.payments
    bulk_ops = []

    for payment_id, p_info in payments_data.items():
        doc = {
            "payment_id": payment_id,
            "user_id": p_info.get("user_id"),
            "amount": p_info.get("amount", 0),
            "status": p_info.get("status"),
            "method": p_info.get("method"),
            "timestamp": p_info.get("timestamp"),
            "type": p_info.get("type"),
            "period": p_info.get("period")
        }
        bulk_ops.append(doc)

    if bulk_ops:
        for op in bulk_ops:
            payments_col.replace_one({"payment_id": op["payment_id"]}, op, upsert=True)
        logging.info(f"Migrated {len(bulk_ops)} payments.")

def main():
    logging.info("Starting migration...")
    client = get_client()
    db = client[DB_NAME]

    users_data = safe_load_json('users.json')
    migrate_users(db, users_data)

    configs_data = safe_load_json('configs.json')
    migrate_configs(db, configs_data)

    payments_data = safe_load_json('payments.json')
    migrate_payments(db, payments_data)

    logging.info("Migration completed successfully.")

if __name__ == "__main__":
    main()
