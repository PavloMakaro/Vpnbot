import json
import os
import sys

# Default client, can be injected for mocking
client = None

def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def migrate():
    global client
    if client is None:
        try:
            import pymongo
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
            client = pymongo.MongoClient(mongo_uri)
        except ImportError:
            print("pymongo is required. Install it using 'pip install pymongo<4'")
            sys.exit(1)

    db = client['vpn_bot']

    # Migrate Users
    users_coll = db['users']
    users_data = load_data('users.json')
    if users_data:
        print(f"Migrating {len(users_data)} users...")
        for uid, udata in users_data.items():
            # Update ID to match Telegram string format
            udata['_id'] = str(uid)
            users_coll.update_one({'_id': udata['_id']}, {'$set': udata}, upsert=True)
        print("Users migrated.")

    # Migrate Configs
    configs_coll = db['configs']
    configs_data = load_data('configs.json')
    if configs_data:
        config_count = sum(len(cfgs) for cfgs in configs_data.values())
        print(f"Migrating {config_count} configs...")
        for period, configs_list in configs_data.items():
            for cfg in configs_list:
                # Add period and unique ID
                cfg['period'] = period
                if '_id' not in cfg:
                     cfg['_id'] = cfg.get('link', cfg['name']) # Fallback id
                configs_coll.update_one({'_id': cfg['_id']}, {'$set': cfg}, upsert=True)
        print("Configs migrated.")

    # Migrate Payments
    payments_coll = db['payments']
    payments_data = load_data('payments.json')
    if payments_data:
        print(f"Migrating {len(payments_data)} payments...")
        for pid, pdata in payments_data.items():
            pdata['_id'] = pid
            payments_coll.update_one({'_id': pid}, {'$set': pdata}, upsert=True)
        print("Payments migrated.")

if __name__ == "__main__":
    migrate()
    print("Migration complete!")