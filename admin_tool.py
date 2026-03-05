import os
import sys
import datetime
import argparse
from pymongo import MongoClient

def upload_configs(filepath, period, mongo_uri):
    try:
        client = MongoClient(mongo_uri)
        client.admin.command('ping')
        db = client.vpn_bot
        configs_coll = db.configs
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        sys.exit(1)

    try:
        with open(filepath, 'r') as f:
            links = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        sys.exit(1)

    if not links:
        print("No valid links found in the file.")
        return

    count = 0
    now = datetime.datetime.now()
    base_name = f"Config_{period}_{now.strftime('%Y%m%d_%H%M%S')}"

    for idx, link in enumerate(links, start=1):
        doc = {
            'name': f"{base_name}_{idx}",
            'link': link,
            'code': f"code_{period}_{now.strftime('%H%M%S')}_{idx}", # generate a dummy code
            'used': False,
            'period': period,
            'uploaded_at': now
        }

        # Upsert by link to avoid duplicates
        result = configs_coll.update_one({'link': link}, {'$setOnInsert': doc}, upsert=True)
        if result.upserted_id:
            count += 1

    print(f"Successfully uploaded {count} new configurations for period '{period}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk upload VPN configs to MongoDB")
    parser.add_argument('file', help="Path to text file containing config links (one per line)")
    parser.add_argument('period', choices=['1_month', '2_months', '3_months'], help="Subscription period for these configs")

    args = parser.parse_args()

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("Error: MONGO_URI environment variable not set.")
        sys.exit(1)

    upload_configs(args.file, args.period, mongo_uri)