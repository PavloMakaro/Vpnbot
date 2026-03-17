import os
import sys
import datetime
from pymongo import MongoClient

# Global client for testing injection
client = None

def upload_configs(period, links):
    global client
    mongo_uri = os.getenv('MONGO_URI')

    if client is None:
        if not mongo_uri:
            print("MONGO_URI environment variable not set.")
            sys.exit(1)
        client = MongoClient(mongo_uri)

    db = client.vpn_bot
    configs_col = db.configs

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    count = 0
    for i, link in enumerate(links):
        link = link.strip()
        if not link:
            continue

        config_name = f"Config_{timestamp}_{i+1}"
        config_doc = {
            'name': config_name,
            'link': link,
            'code': f"code_{timestamp}_{i+1}",
            'used': False,
            'period': period
        }

        # Check if link already exists
        if configs_col.find_one({'link': link}):
            print(f"Skipping link {link} as it already exists in the database.")
            continue

        configs_col.insert_one(config_doc)
        count += 1

    print(f"Successfully uploaded {count} configs for period '{period}'.")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python admin_tool.py <period> <link1> [link2 ...]")
        print("Example: python admin_tool.py 1_month vless://link1 vless://link2")
        sys.exit(1)

    period = sys.argv[1]
    links = sys.argv[2:]

    upload_configs(period, links)
