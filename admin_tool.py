import os
import argparse
from datetime import datetime
from pymongo import MongoClient

def upload_configs(db, period, links):
    configs_col = db.configs
    count = 0
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d%H%M%S")
    for i, link in enumerate(links):
        link = link.strip()
        if not link:
            continue
        config_name = f"Config_{period}_{timestamp_str}_{i+1}"
        doc = {
            "period": period,
            "name": config_name,
            "link": link,
            "used": False
        }
        configs_col.update_one({"link": link}, {"$set": doc}, upsert=True)
        count += 1
    print(f"Uploaded {count} configs for period {period}.")

def main():
    parser = argparse.ArgumentParser(description="Upload configurations to MongoDB.")
    parser.add_argument("--uri", help="MongoDB connection URI.", required=True)
    parser.add_argument("--db", help="Target database name.", default="vpn_bot")
    parser.add_argument("--period", help="Subscription period (e.g., 1_month).", required=True)
    parser.add_argument("--file", help="File containing configuration links, one per line.", required=True)
    args = parser.parse_args()

    client = MongoClient(args.uri)
    db = client[args.db]

    try:
        with open(args.file, "r") as f:
            links = f.readlines()
    except FileNotFoundError:
        print(f"File {args.file} not found.")
        return

    upload_configs(db, args.period, links)

if __name__ == "__main__":
    main()