import os
import sys
import logging
import argparse
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get MongoDB connection string from environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "vpn_bot"

client = None

def get_client():
    global client
    if client is None:
        try:
            client = MongoClient(MONGO_URI)
            # Test connection
            client.admin.command('ping')
        except ConnectionFailure as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            sys.exit(1)
    return client

def add_configs(period, links):
    """
    Adds a list of config links for a specific period to MongoDB.
    Generates unique names based on timestamps.
    """
    if not links:
        logging.warning("No links provided to add.")
        return

    client = get_client()
    db = client[DB_NAME]
    configs_col = db.configs

    bulk_ops = []
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    for i, link in enumerate(links):
        clean_link = link.strip()
        if not clean_link:
            continue

        name = f"Config_{period}_{timestamp}_{i+1}"

        # In a real scenario you might also need a "code", we'll generate a dummy one here
        # similar to the old script, or just leave it empty if not needed
        code = f"code_{period}_{timestamp}_{i+1}"

        doc = {
            "name": name,
            "link": clean_link,
            "code": code,
            "used": False,
            "period": period
        }
        bulk_ops.append(doc)

    if bulk_ops:
        try:
            # We just insert them
            configs_col.insert_many(bulk_ops)
            logging.info(f"Successfully added {len(bulk_ops)} configs for period '{period}'.")
        except Exception as e:
             logging.error(f"Failed to insert configs: {e}")
    else:
        logging.warning("No valid links were processed.")

def main():
    parser = argparse.ArgumentParser(description="Admin Tool for VPN Bot Configurations")
    parser.add_argument('--period', required=True, help="Subscription period (e.g., '1_month', '2_months')")
    parser.add_argument('--file', help="Path to a text file containing config links (one per line)")
    parser.add_argument('--links', nargs='+', help="Space-separated list of config links")

    args = parser.parse_args()

    links_to_add = []

    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                links_to_add.extend(f.readlines())
        except FileNotFoundError:
            logging.error(f"File not found: {args.file}")
            sys.exit(1)
        except OSError as e:
            logging.error(f"Error reading file {args.file}: {e}")
            sys.exit(1)

    if args.links:
        links_to_add.extend(args.links)

    if not links_to_add:
        logging.error("No links provided. Use --file or --links.")
        sys.exit(1)

    add_configs(args.period, links_to_add)

if __name__ == "__main__":
    main()
