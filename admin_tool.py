import os
import sys
import uuid
from pymongo import MongoClient
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://admin:admin@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.getenv("MONGO_DB_NAME", "vpn_bot_db")

def connect_db():
    try:
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        return client[DB_NAME]
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

def bulk_upload_configs(db, period, links):
    """
    Bulk uploads configs to the database.
    Generates names based on a base name and timestamp, plus a counter.
    """
    configs_collection = db['configs']
    added_count = 0

    timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')

    for i, link in enumerate(links, 1):
        if not link.strip():
            continue

        config_name = f"Config_{period}_{timestamp_str}_{i}"
        config_code = f"code_{period}_{timestamp_str}_{i}"

        config_doc = {
            'period': period,
            'name': config_name,
            'link': link.strip(),
            'code': config_code,
            'used': False
        }

        try:
            configs_collection.update_one({'link': config_doc['link']}, {'$set': config_doc}, upsert=True)
            added_count += 1
        except Exception as e:
            print(f"Error adding config {link}: {e}")

    return added_count

def main():
    if len(sys.argv) < 3:
        print("Usage: python admin_tool.py <period> <path_to_links_file>")
        print("Example: python admin_tool.py 1_month configs.txt")
        sys.exit(1)

    period = sys.argv[1]
    filepath = sys.argv[2]

    # Optional check based on known periods
    valid_periods = ['1_month', '2_months', '3_months']
    if period not in valid_periods:
         print(f"Warning: '{period}' is not a recognized standard period ({', '.join(valid_periods)}).")
         confirm = input("Continue anyway? (y/n): ")
         if confirm.lower() != 'y':
             print("Aborting.")
             sys.exit(0)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            links = f.readlines()
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)

    db = connect_db()

    print(f"Attempting to upload {len(links)} links for period '{period}'...")
    added = bulk_upload_configs(db, period, links)
    print(f"Successfully added/updated {added} configs.")

if __name__ == "__main__":
    main()
