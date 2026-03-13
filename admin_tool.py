import sys
import os
import pymongo
from typing import Optional
import datetime

client: Optional[pymongo.MongoClient] = None

def get_db():
    global client
    if client is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        client = pymongo.MongoClient(mongo_uri)
    return client["vpn_bot"]

def add_configs(period, links):
    db = get_db()
    configs_coll = db["configs"]

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    operations = []
    for i, link in enumerate(links):
        link = link.strip()
        if not link:
            continue
        config_name = f"Config_{period}_{timestamp}_{i+1}"
        doc = {
            "name": config_name,
            "link": link,
            "code": f"code_{period}_{timestamp}_{i+1}",
            "used": False,
            "period": period
        }
        operations.append(pymongo.InsertOne(doc))

    if operations:
        configs_coll.bulk_write(operations)
        print(f"Successfully added {len(operations)} configs for period {period}.")
    else:
        print("No valid configs provided.")

def print_usage():
    print("Usage: python admin_tool.py <period> <link1> [<link2> ...]")
    print("Example: python admin_tool.py 1_month vless://link1 vless://link2")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    period = sys.argv[1]
    links = sys.argv[2:]
    add_configs(period, links)
