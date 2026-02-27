import os
import time
from pymongo import MongoClient

# Connection string to your MongoDB Atlas
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "vpn_bot"

def upload_configs(db, period_key, file_path):
    configs_coll = db["configs"]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            links = f.readlines()

        count = 0
        for i, link in enumerate(links, 1):
            link = link.strip()
            if not link:
                continue

            doc = {
                "period": period_key,
                "name": f"Config_{period_key}_{int(time.time())}_{i}",
                "link": link,
                "code": f"code_{period_key}_{int(time.time())}_{i}",
                "used": False,
                "assigned_to": None,
                "created_at": time.time()
            }

            # Upsert by link to avoid duplicates
            result = configs_coll.update_one({"link": link}, {"$setOnInsert": doc}, upsert=True)
            if result.upserted_id:
                count += 1

        print(f"Uploaded {count} new configs for period '{period_key}'.")

    except FileNotFoundError:
        print(f"File not found: {file_path}")

def main():
    print("Admin Tool for Bulk Config Upload")
    print("Periods: 1_month, 2_months, 3_months")

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    while True:
        period = input("\nEnter period key (or 'exit'): ").strip()
        if period == 'exit':
            break

        file_path = input("Enter path to file with config links (one per line): ").strip()

        if period and file_path:
            upload_configs(db, period, file_path)

if __name__ == "__main__":
    main()
