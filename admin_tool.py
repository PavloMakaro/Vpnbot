import argparse
import datetime
import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")

def upload_configs(period, filepath):
    if not MONGO_URI:
        print("MONGO_URI environment variable is not set")
        return

    client = MongoClient(MONGO_URI)
    db = client["vpn_bot"]
    configs_collection = db["configs"]

    with open(filepath, "r") as f:
        links = f.read().splitlines()

    configs_to_insert = []
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    for idx, link in enumerate(links):
        if not link.strip():
            continue
        config = {
            "name": f"Config_{period}_{timestamp}_{idx}",
            "link": link.strip(),
            "code": f"code_{period}_{timestamp}_{idx}",
            "used": False,
            "period": period
        }
        configs_to_insert.append(config)

    if configs_to_insert:
        configs_collection.insert_many(configs_to_insert)
        print(f"Successfully uploaded {len(configs_to_insert)} configs for period {period}.")
    else:
        print("No valid links found in the file.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload configs to MongoDB")
    parser.add_argument("period", type=str, help="Subscription period (e.g., 1_month)")
    parser.add_argument("filepath", type=str, help="Path to a text file containing config links, one per line")
    args = parser.parse_args()

    upload_configs(args.period, args.filepath)
