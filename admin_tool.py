import os
from datetime import datetime
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client['vpn']
configs_col = db['configs']

def bulk_upload_configs(period_key, links):
    count = 0
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    for i, link in enumerate(links):
        link = link.strip()
        if not link:
            continue

        name = f"Config_{period_key}_{timestamp}_{i}"
        doc = {
            "name": name,
            "link": link,
            "code": f"code_{period_key}_{timestamp}_{i}",
            "used": False,
            "period": period_key
        }
        configs_col.update_one({"link": doc["link"]}, {"$set": doc}, upsert=True)
        count += 1
    return count

if __name__ == "__main__":
    print("Bulk Config Uploader")
    period = input("Enter period (1_month, 2_months, 3_months): ")
    if period not in ['1_month', '2_months', '3_months']:
        print("Invalid period.")
        exit(1)

    print("Paste your links (one per line). Press Enter twice to finish:")
    links = []
    while True:
        line = input()
        if not line:
            break
        links.append(line)

    if not links:
        print("No links provided.")
        exit(0)

    uploaded = bulk_upload_configs(period, links)
    print(f"Successfully uploaded {uploaded} configs for period '{period}'.")