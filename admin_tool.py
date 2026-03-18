import os
import pymongo
from datetime import datetime

# Allow overriding client for testing (mock)
client = None

def get_client():
    global client
    if client is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        client = pymongo.MongoClient(mongo_uri)
    return client

def bulk_upload_configs(period, config_links):
    """Bulk upload configuration links to the configs collection with timestamp-based names."""
    if not config_links:
        print("No configs to upload.")
        return 0

    db_client = get_client()
    db = db_client['vpn_bot']
    configs_col = db['configs']

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    docs_to_insert = []

    for idx, link in enumerate(config_links):
        if not link.strip():
            continue
        # Generate unique name based on timestamp
        unique_name = f"Config_{timestamp}_{idx + 1}"
        doc = {
            'period': period,
            'name': unique_name,
            'link': link.strip(),
            'code': f"code_{period}_{idx + 1}",
            'used': False
        }
        docs_to_insert.append(doc)

    if docs_to_insert:
        try:
            configs_col.insert_many(docs_to_insert)
            print(f"Successfully inserted {len(docs_to_insert)} configs for period {period}.")
            return len(docs_to_insert)
        except Exception as e:
            print(f"Failed to insert configs: {e}")
            return 0
    else:
        print("No valid configs found in input.")
        return 0

if __name__ == "__main__":
    period = input("Enter subscription period (e.g., 1_month, 2_months, 3_months): ")
    print("Enter config links one per line. Press Enter twice to finish:")
    links = []
    while True:
        line = input()
        if not line:
            break
        links.append(line)

    bulk_upload_configs(period, links)
