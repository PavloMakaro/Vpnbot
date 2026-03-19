import sys
import datetime
import os

# Default client, can be injected for mocking
client = None

def upload_configs(period, links):
    global client
    if client is None:
        try:
            import pymongo
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
            client = pymongo.MongoClient(mongo_uri)
        except ImportError:
            print("pymongo is required. Install it using 'pip install pymongo<4'")
            sys.exit(1)

    db = client['vpn_bot']
    configs_coll = db['configs']

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    configs_to_insert = []

    for idx, link in enumerate(links):
        link = link.strip()
        if not link:
            continue

        config_name = f"Config_{period}_{timestamp}_{idx+1}"
        config_data = {
            "_id": link,  # Using link as primary key for simplicity and uniqueness
            "name": config_name,
            "link": link,
            "period": period,
            "used": False,
            "upload_date": datetime.datetime.now().isoformat()
        }
        configs_to_insert.append(config_data)

    if configs_to_insert:
        try:
            result = configs_coll.insert_many(configs_to_insert, ordered=False)
            print(f"Successfully uploaded {len(result.inserted_ids)} configs for {period}.")
        except Exception as e:
            # Handle duplicate keys if trying to insert same link twice
            print(f"Error uploading configs (some may have been duplicates): {e}")

    return len(configs_to_insert)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python admin_tool.py <period> <link1> <link2> ...")
        print("Periods: 1_month, 2_months, 3_months")
        sys.exit(1)

    period = sys.argv[1]
    links = sys.argv[2:]

    upload_configs(period, links)