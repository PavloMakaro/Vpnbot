import argparse
import pymongo
import os
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

def add_configs(file_path, period):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DB_NAME]
        configs_coll = db["configs"]

        with open(file_path, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f.readlines() if line.strip()]

        if not links:
            print("No links found in file.")
            return

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        docs = []
        for i, link in enumerate(links, 1):
            doc = {
                "name": f"VPN_{period}_{timestamp}_{i}",
                "link": link,
                "code": f"code_{period}_{timestamp}_{i}",
                "period": period,
                "used": False,
                "added_at": datetime.now()
            }
            # Add to list only if link doesn't already exist
            if not configs_coll.find_one({"link": link}):
                docs.append(doc)

        if docs:
            result = configs_coll.insert_many(docs)
            print(f"Successfully added {len(result.inserted_ids)} new configs for period '{period}'.")
            print(f"Skipped {len(links) - len(docs)} duplicates.")
        else:
            print("No new configs to add. All links already exist in the database.")

    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk upload VPN configs to MongoDB Atlas.")
    parser.add_argument("file", help="Path to text file containing config links (one per line)")
    parser.add_argument("period", choices=['1_month', '2_months', '3_months'], help="Subscription period")

    args = parser.parse_args()

    print(f"Uploading configs from {args.file} for period {args.period}...")
    add_configs(args.file, args.period)