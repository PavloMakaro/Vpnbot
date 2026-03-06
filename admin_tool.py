import os
import argparse
import datetime
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Let client be overridable for testing
client = None

def get_mongo_client():
    global client
    if client is not None:
        return client

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI environment variable must be set")
    client = MongoClient(mongo_uri)
    return client

def bulk_upload_configs(db, file_path, period):
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]

        if not links:
            logging.warning("No valid links found in the file.")
            return

        configs_coll = db.configs
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        bulk_ops = []
        for i, link in enumerate(links):
            config_name = f"config_{period}_{timestamp}_{i+1}"

            doc = {
                "name": config_name,
                "link": link,
                "code": f"code_{period}_{timestamp}_{i+1}",
                "used": False,
                "period": period
            }

            from pymongo import InsertOne
            bulk_ops.append(InsertOne(doc))

        if bulk_ops:
            result = configs_coll.bulk_write(bulk_ops)
            logging.info(f"Successfully uploaded {result.inserted_count} configs for period '{period}'.")

    except Exception as e:
        logging.error(f"Error during bulk upload: {e}")

def main():
    parser = argparse.ArgumentParser(description="Admin Tool for VPN Bot Configurations")
    parser.add_argument("--file", required=True, help="Path to text file containing configuration links (one per line)")
    parser.add_argument("--period", required=True, choices=["1_month", "2_months", "3_months"], help="Subscription period for these configs")

    args = parser.parse_args()

    try:
        mongo_client = get_mongo_client()
        # Ping the server to check connection
        mongo_client.admin.command('ping')

        db = mongo_client["vpn_bot"]
        bulk_upload_configs(db, args.file, args.period)

    except ConnectionFailure:
        logging.error("Failed to connect to MongoDB. Check MONGO_URI.")
    except ValueError as e:
        logging.error(str(e))
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        if client is not None and getattr(client, "close", None):
            client.close()

if __name__ == "__main__":
    main()