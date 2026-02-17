import json
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# CONFIGURATION
# It's better to use environment variable for connection string
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "vpn_bot"

async def migrate():
    print("Starting migration (Async)...")

    if not MONGO_URI:
        print("Please set MONGO_URI environment variable.")
        return

    # Load JSON files (Synchronous IO for local files is acceptable in migration script,
    # but we can wrap it or just keep it simple as it's a one-off task)
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        print(f"Loaded {len(users_data)} users.")
    except FileNotFoundError:
        users_data = {}
        print("users.json not found.")

    try:
        with open('configs.json', 'r', encoding='utf-8') as f:
            configs_data = json.load(f)
        print(f"Loaded configs.")
    except FileNotFoundError:
        configs_data = {}
        print("configs.json not found.")

    try:
        with open('payments.json', 'r', encoding='utf-8') as f:
            payments_data = json.load(f)
        print(f"Loaded {len(payments_data)} payments.")
    except FileNotFoundError:
        payments_data = {}
        print("payments.json not found.")

    # Connect to MongoDB (Async)
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    # 1. Migrate Users
    users_coll = db['users']
    if users_data:
        users_ops = []
        for user_id, user_info in users_data.items():
            sub_end = user_info.get('subscription_end')
            if sub_end:
                try:
                    sub_end = datetime.strptime(sub_end, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass

            doc = {
                '_id': str(user_id),
                'username': user_info.get('username'),
                'first_name': user_info.get('first_name'),
                'balance': user_info.get('balance', 0),
                'subscription_end': sub_end,
                'referrals_count': user_info.get('referrals_count', 0),
                'referred_by': user_info.get('referred_by'),
                'used_configs': user_info.get('used_configs', [])
            }
            # Motor doesn't have bulk_write like pymongo, but we can iterate.
            # Or use bulk_write with pymongo operations if needed.
            # For simplicity and clarity in async loop:
            await users_coll.update_one({'_id': str(user_id)}, {'$set': doc}, upsert=True)

        print(f"Users migration step completed.")

    # 2. Migrate Configs
    configs_coll = db['configs']
    if configs_data:
        for period, config_list in configs_data.items():
            for conf in config_list:
                doc = {
                    'period': period,
                    'name': conf.get('name'),
                    'link': conf.get('link'),
                    'code': conf.get('code'),
                    'used': conf.get('used', False)
                }
                if conf.get('link'):
                    await configs_coll.update_one({'link': conf.get('link')}, {'$set': doc}, upsert=True)

        print(f"Configs migration step completed.")

    # 3. Migrate Payments
    payments_coll = db['payments']
    if payments_data:
        for payment_id, p_data in payments_data.items():
            doc = {
                '_id': str(payment_id),
                'user_id': str(p_data.get('user_id')),
                'amount': p_data.get('amount'),
                'status': p_data.get('status'),
                'timestamp': p_data.get('timestamp'),
                'method': p_data.get('method'),
                'type': p_data.get('type')
            }
            await payments_coll.update_one({'_id': str(payment_id)}, {'$set': doc}, upsert=True)

        print(f"Payments migration step completed.")

    print("Migration complete.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(migrate())
