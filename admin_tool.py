import os
import argparse
from datetime import datetime
from pymongo import MongoClient

# Setup default connection string
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "vpn_bot"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
configs_col = db['configs']

def bulk_upload_configs(period, filepath):
    """
    Reads a file with configuration links (one per line) and uploads them
    to the MongoDB 'configs' collection with a unique name based on timestamp.
    """
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]

    if not links:
        print("Error: No valid links found in the file.")
        return

    print(f"Found {len(links)} links for period '{period}'.")

    docs = []
    timestamp_prefix = datetime.now().strftime("%Y%m%d%H%M%S")

    for i, link in enumerate(links, 1):
        doc = {
            'name': f"Config_{timestamp_prefix}_{i}",
            'link': link,
            'code': f"Code_{timestamp_prefix}_{i}",
            'used': False,
            'period': period,
            'assigned_to': None,
            'uploaded_at': datetime.now()
        }
        docs.append(doc)

    if docs:
        result = configs_col.insert_many(docs)
        print(f"Successfully uploaded {len(result.inserted_ids)} configurations.")

def show_stats():
    """
    Shows basic statistics about the configs collection.
    """
    pipeline = [
        {"$group": {"_id": {"period": "$period", "used": "$used"}, "count": {"$sum": 1}}}
    ]
    results = list(configs_col.aggregate(pipeline))

    print("\nConfiguration Statistics:")
    print("-" * 40)

    stats = {}
    for res in results:
        period = res['_id']['period']
        used = res['_id']['used']
        count = res['count']

        if period not in stats:
            stats[period] = {'used': 0, 'available': 0}

        if used:
            stats[period]['used'] += count
        else:
            stats[period]['available'] += count

    for period, counts in stats.items():
        print(f"Period: {period}")
        print(f"  Available: {counts['available']}")
        print(f"  Used:      {counts['used']}")
        print(f"  Total:     {counts['available'] + counts['used']}")
        print("-" * 40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Admin Tool for Config Upload")
    parser.add_argument("--uri", type=str, help="MongoDB URI", default=MONGO_URI)
    parser.add_argument("--upload", type=str, help="Path to file containing config links")
    parser.add_argument("--period", type=str, help="Subscription period (e.g., 1_month, 2_months)", choices=['1_month', '2_months', '3_months'])
    parser.add_argument("--stats", action="store_true", help="Show configuration statistics")

    args = parser.parse_args()

    if args.uri:
        client = MongoClient(args.uri)
        db = client[DB_NAME]
        configs_col = db['configs']

    if args.upload:
        if not args.period:
            print("Error: --period is required when uploading configs.")
        else:
            bulk_upload_configs(args.period, args.upload)

    if args.stats or not args.upload:
        show_stats()
