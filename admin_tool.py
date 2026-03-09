import argparse
import os
import pymongo
from datetime import datetime

# Target MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

def upload_configs(db, filepath, period):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    configs_coll = db['configs']
    added_count = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        config_name = f"Config_{period}_{timestamp}"

        doc = {
            'name': config_name,
            'link': line,
            'code': '',
            'used': False,
            'period': period
        }

        # Check if link already exists
        if not configs_coll.find_one({'link': line}):
            configs_coll.insert_one(doc)
            added_count += 1
        else:
            print(f"Config link already exists, skipping: {line[:30]}...")

    print(f"Successfully uploaded {added_count} configurations for period '{period}'.")

def main():
    parser = argparse.ArgumentParser(description="Bulk upload VPN configurations to MongoDB.")
    parser.add_argument("filepath", help="Path to a text file containing config links (one per line).")
    parser.add_argument("period", help="Subscription period key (e.g., '1_month', '2_months', '3_months').")

    args = parser.parse_args()

    print(f"Connecting to MongoDB: {MONGO_URI}")

    # Allow injection of client for testing
    global client
    if 'client' not in globals():
        client = pymongo.MongoClient(MONGO_URI)

    db = client['vpn_bot']

    upload_configs(db, args.filepath, args.period)

if __name__ == "__main__":
    main()