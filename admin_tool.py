import os
import argparse
from datetime import datetime
from pymongo import MongoClient

def get_db():
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(MONGO_URI)
    return client["vpn_bot"]

def main():
    parser = argparse.ArgumentParser(description="Admin Tool for VPN Bot (MongoDB)")
    parser.add_argument("--period", required=True, choices=["1_month", "2_months", "3_months"], help="Subscription period key")
    parser.add_argument("--file", required=True, help="File containing config links (one per line)")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        return

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    if not links:
        print("No valid links found in the file.")
        return

    db = get_db()
    configs_collection = db.configs

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    bulk_ops = []

    for i, link in enumerate(links):
        unique_name = f"Config_{args.period}_{timestamp}_{i+1}"

        # Simple extraction of code if it's a vless URL
        code = ""
        if "vless://" in link:
            parts = link.split("@")
            if len(parts) > 1:
               code = parts[0].replace("vless://", "")

        conf_doc = {
            "period": args.period,
            "name": unique_name,
            "link": link,
            "code": code,
            "used": False
        }
        bulk_ops.append(conf_doc)

    try:
        configs_collection.insert_many(bulk_ops)
        print(f"Successfully uploaded {len(bulk_ops)} configs for period '{args.period}'.")
    except Exception as e:
         print(f"Error uploading configs: {e}")

if __name__ == "__main__":
    main()