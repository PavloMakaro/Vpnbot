import json
import os
import sys
from datetime import datetime

# Try to import pymongo
try:
    from pymongo import MongoClient
except ImportError:
    print("Error: pymongo is not installed. Please install it with: pip install pymongo")
    sys.exit(1)

# Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

def load_json(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found, skipping.")
        return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return {}

def migrate():
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
    except Exception as e:
        print(f"Connection error: {e}")
        return

    # --- Users ---
    users_data = load_json('users.json')
    if users_data:
        print(f"Migrating {len(users_data)} users...")
        users_col = db['users']
        ops = []
        for uid, udata in users_data.items():
            udata['_id'] = str(uid)
            # Ensure proper types
            if 'balance' in udata:
                udata['balance'] = float(udata['balance'])
            # Convert date strings to datetime if possible, or leave as string
            # App Services logic used 'subscription_end' as string in some places, but Date object in JS
            # Let's try to convert for better querying
            if udata.get('subscription_end'):
                try:
                    udata['subscription_end'] = datetime.strptime(udata['subscription_end'], '%Y-%m-%d %H:%M:%S')
                except:
                    pass # Keep as string if format differs

            # Handle used_configs dates
            if 'used_configs' in udata:
                for uc in udata['used_configs']:
                    if 'issue_date' in uc:
                         try:
                            uc['issue_date'] = datetime.strptime(uc['issue_date'], '%Y-%m-%d %H:%M:%S')
                         except:
                            pass

            ops.append(udata)

        if ops:
            try:
                # Use bulk_write or insert_many with ordered=False to ignore duplicates
                # For simplicity here using insert_many with fallback
                try:
                    users_col.insert_many(ops, ordered=False)
                except Exception as e:
                    print(f"Some users might already exist: {e}")
                print("Users migration done.")
            except Exception as e:
                print(f"Error migrating users: {e}")

    # --- Configs ---
    configs_data = load_json('configs.json')
    if configs_data:
        print("Migrating configs...")
        configs_col = db['configs']
        ops = []
        for period, cfg_list in configs_data.items():
            for cfg in cfg_list:
                cfg['period'] = period
                # Ideally check if 'link' is unique or use some ID
                # We can generate an _id or let Mongo do it
                ops.append(cfg)

        if ops:
            try:
                configs_col.insert_many(ops, ordered=False)
                print(f"Migrated {len(ops)} configs.")
            except Exception as e:
                print(f"Error migrating configs: {e}")

    # --- Payments ---
    payments_data = load_json('payments.json')
    if payments_data:
        print(f"Migrating {len(payments_data)} payments...")
        payments_col = db['payments']
        ops = []
        for pid, pdata in payments_data.items():
            pdata['_id'] = pid
            if 'amount' in pdata:
                pdata['amount'] = float(pdata['amount'])
            ops.append(pdata)

        if ops:
            try:
                payments_col.insert_many(ops, ordered=False)
                print("Payments migration done.")
            except Exception as e:
                 print(f"Error migrating payments: {e}")

    print("\nMigration completed.")
    print("NOTE: Please ensure you set the correct MONGO_URI in the script or environment variable.")

if __name__ == "__main__":
    if "mongodb+srv://<username>" in MONGO_URI:
        print("WARNING: Default MONGO_URI detected. Please edit the script or set MONGO_URI env var.")
    migrate()
