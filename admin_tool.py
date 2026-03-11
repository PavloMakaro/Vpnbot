import pymongo
import os
import sys
import datetime

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "vpn_bot"

try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    configs_col = db['configs']
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    sys.exit(1)

def add_configs_bulk(period, links):
    if not links:
        print("No links provided.")
        return

    added = 0
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for i, link in enumerate(links):
        link = link.strip()
        if not link:
            continue

        name = f"Config_{period}_{now_str}_{i+1}"
        code = f"code_{period}_{now_str}_{i+1}"

        doc = {
            "period": period,
            "name": name,
            "link": link,
            "code": code,
            "used": False
        }

        configs_col.update_one({"link": link}, {"$set": doc}, upsert=True)
        added += 1

    print(f"Successfully added/updated {added} configs for period '{period}'.")

if __name__ == "__main__":
    print("=== Admin Tool: Bulk Add Configs ===")
    period = input("Enter period (e.g., '1_month', '2_months', '3_months'): ").strip()

    if not period:
        print("Period is required.")
        sys.exit(0)

    print("Paste your config links. Enter an empty line when finished:")
    links = []
    while True:
        try:
            line = input()
            if not line.strip():
                break
            links.append(line)
        except EOFError:
            break

    add_configs_bulk(period, links)
