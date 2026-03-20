import argparse
import sys
import datetime
from pymongo import MongoClient

# For testing with mongomock
client = None

def get_client(uri: str):
    global client
    if client is None:
        client = MongoClient(uri)
    return client

def bulk_upload_configs(uri: str, period: str, filepath: str):
    mongo_client = get_client(uri)
    db = mongo_client.vpn_bot
    configs_collection = db.configs

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            links = f.read().splitlines()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        sys.exit(1)

    # Filter out empty lines
    links = [link.strip() for link in links if link.strip()]

    if not links:
        print("No valid links found in the file.")
        sys.exit(0)

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    added_count = 0

    for idx, link in enumerate(links, start=1):
        doc = {
            'period': period,
            'name': f"Config_{period}_{timestamp}_{idx}",
            'link': link,
            'code': f"code_{period}_{timestamp}_{idx}",
            'used': False
        }

        # Avoid inserting duplicate links
        result = configs_collection.update_one(
            {'link': doc['link']},
            {'$setOnInsert': doc},
            upsert=True
        )

        if result.upserted_id:
            added_count += 1

    print(f"Successfully added {added_count} configurations for period '{period}'.")
    if added_count < len(links):
        print(f"{len(links) - added_count} duplicates were skipped.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Admin Tool: Bulk Upload VPN Configs to MongoDB")
    parser.add_argument('--uri', type=str, required=True, help="MongoDB connection URI")
    parser.add_argument('--period', type=str, required=True, help="Subscription period (e.g., '1_month', '3_months')")
    parser.add_argument('--file', type=str, required=True, help="Path to text file containing config links (one per line)")

    args = parser.parse_args()
    bulk_upload_configs(args.uri, args.period, args.file)
