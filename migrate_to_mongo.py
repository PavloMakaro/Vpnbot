import json
import os
from pymongo import MongoClient
import argparse

def migrate_users(db, users_file):
    try:
        with open(users_file, "r") as f:
            users_data = json.load(f)
    except FileNotFoundError:
        print(f"File {users_file} not found. Skipping.")
        return

    users_col = db.users
    count = 0
    for user_id, data in users_data.items():
        doc = {"telegram_id": str(user_id), **data}
        if "_id" in doc:
            del doc["_id"]
        users_col.update_one({"telegram_id": str(user_id)}, {"$set": doc}, upsert=True)
        count += 1
    print(f"Migrated {count} users.")

def migrate_configs(db, configs_file):
    try:
        with open(configs_file, "r") as f:
            configs_data = json.load(f)
    except FileNotFoundError:
        print(f"File {configs_file} not found. Skipping.")
        return

    configs_col = db.configs
    count = 0
    for period, configs in configs_data.items():
        for config in configs:
            doc = {"period": period, **config}
            configs_col.update_one({"link": config["link"]}, {"$set": doc}, upsert=True)
            count += 1
    print(f"Migrated {count} configs.")

def migrate_payments(db, payments_file):
    try:
        with open(payments_file, "r") as f:
            payments_data = json.load(f)
    except FileNotFoundError:
        print(f"File {payments_file} not found. Skipping.")
        return

    payments_col = db.payments
    count = 0
    for payment_id, payment in payments_data.items():
        doc = {"payment_id": payment_id, **payment}
        payments_col.update_one({"payment_id": payment_id}, {"$set": doc}, upsert=True)
        count += 1
    print(f"Migrated {count} payments.")

def main():
    parser = argparse.ArgumentParser(description="Migrate local JSON files to MongoDB.")
    parser.add_argument("--uri", help="MongoDB connection URI.", required=True)
    parser.add_argument("--db", help="Target database name.", default="vpn_bot")
    parser.add_argument("--dir", help="Directory containing JSON files.", default=".")
    args = parser.parse_args()

    client = MongoClient(args.uri)
    db = client[args.db]

    users_file = os.path.join(args.dir, "users.json")
    configs_file = os.path.join(args.dir, "configs.json")
    payments_file = os.path.join(args.dir, "payments.json")

    migrate_users(db, users_file)
    migrate_configs(db, configs_file)
    migrate_payments(db, payments_file)

if __name__ == "__main__":
    main()