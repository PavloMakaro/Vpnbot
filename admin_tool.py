import sys
import os
import datetime
from pymongo import MongoClient

# For testing override
client = None

def get_client():
    global client
    if client is None:
        client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    return client

def add_configs(period, links):
    db = get_client().vpn_bot
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    docs = []
    for i, link in enumerate(links):
        link = link.strip()
        if not link:
            continue

        doc = {
            "period": period,
            "name": f"Config_{period}_{timestamp}_{i}",
            "link": link,
            "code": f"code_{period}_{timestamp}_{i}",
            "used": False
        }
        docs.append(doc)

    if docs:
        db.configs.insert_many(docs)
        print(f"Successfully added {len(docs)} configs for period {period}.")
    else:
        print("No valid links provided.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python admin_tool.py <period> <link1> <link2> ...")
        sys.exit(1)

    period = sys.argv[1]
    links = sys.argv[2:]
    add_configs(period, links)