import argparse
import os
import sys
import time
from pymongo import MongoClient

def main():
    parser = argparse.ArgumentParser(description="Admin Tool for uploading VPN Configs to MongoDB")
    parser.add_argument('period', type=str, choices=['1_month', '2_months', '3_months'], help="Subscription period key")
    parser.add_argument('file', type=str, help="Path to text file containing config links (one per line)")

    args = parser.parse_help() if len(sys.argv) == 1 else parser.parse_args()

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("Error: MONGO_URI environment variable is not set.")
        sys.exit(1)

    if not os.path.exists(args.file):
        print(f"Error: File {args.file} not found.")
        sys.exit(1)

    try:
        client = MongoClient(mongo_uri)
        db = client['vpn_bot']
        configs_collection = db['configs']

        with open(args.file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            print("No links found in the file.")
            sys.exit(0)

        timestamp = int(time.time())
        configs_to_insert = []
        for i, link in enumerate(lines):
            config_doc = {
                'period': args.period,
                'name': f"Config_{args.period}_{timestamp}_{i+1}",
                'link': link,
                'code': f"code_{args.period}_{timestamp}_{i+1}",
                'used': False
            }
            configs_to_insert.append(config_doc)

        result = configs_collection.insert_many(configs_to_insert)
        print(f"Successfully uploaded {len(result.inserted_ids)} configs for {args.period}.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
