import argparse
import sys
import datetime
from pymongo import MongoClient

# Configuration
MONGO_URI = "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "vpn_bot"

def add_configs(period, file_path, uri):
    client = MongoClient(uri)
    db = client[DB_NAME]
    configs_coll = db['configs']

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return

    bulk_configs = []
    for i, link in enumerate(lines, 1):
        # Generate name and code
        # Name format: Config_<period>_<timestamp>_<index> (unique enough)
        ts = int(datetime.datetime.now().timestamp())
        name = f"Config_{period}_{ts}_{i}"
        code = f"code_{period}_{ts}_{i}" # If code is needed separately

        doc = {
            "name": name,
            "link": link,
            "code": code,
            "period": period,
            "used": False,
            "created_at": datetime.datetime.now()
        }
        bulk_configs.append(doc)

    if bulk_configs:
        result = configs_coll.insert_many(bulk_configs)
        print(f"Successfully added {len(result.inserted_ids)} configs for period '{period}'.")
    else:
        print("No valid configs found in file.")

def main():
    parser = argparse.ArgumentParser(description="Admin Tool for VPN Bot")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add Configs Command
    add_parser = subparsers.add_parser("add_configs", help="Add configs from file")
    add_parser.add_argument("period", type=str, help="Subscription period (e.g., 1_month, 2_months)")
    add_parser.add_argument("file", type=str, help="Path to file containing config links (one per line)")
    add_parser.add_argument("--uri", type=str, default=MONGO_URI, help="MongoDB URI")

    args = parser.parse_args()

    if args.command == "add_configs":
        if args.uri == MONGO_URI and "<username>" in MONGO_URI:
            print("Please provide --uri argument or edit the script with your MongoDB URI.")
            return
        add_configs(args.period, args.file, args.uri)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
