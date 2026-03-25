import argparse
import os
import datetime
from pymongo import MongoClient

# MongoDB connection settings. Can be overridden with env vars.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "vpn_bot")

def main():
    parser = argparse.ArgumentParser(description="Bulk upload VPN configs to MongoDB")
    parser.add_argument("period", choices=["1_month", "2_months", "3_months"], help="Subscription period")
    parser.add_argument("file", help="Path to text file containing config links (one per line)")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        return

    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    configs_collection = db["configs"]

    with open(args.file, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]

    if not links:
        print("No valid links found in the file.")
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    configs_to_insert = []

    for i, link in enumerate(links, start=1):
        config_name = f"Config_{args.period}_{timestamp}_{i}"

        configs_to_insert.append({
            "name": config_name,
            "link": link,
            "code": f"code_{args.period}_{timestamp}_{i}", # Example code generation
            "period": args.period,
            "used": False
        })

    if configs_to_insert:
        result = configs_collection.insert_many(configs_to_insert)
        print(f"Successfully inserted {len(result.inserted_ids)} configs for period '{args.period}'.")
    else:
        print("No configs to insert.")

if __name__ == "__main__":
    main()
