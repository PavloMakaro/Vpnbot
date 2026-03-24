import os
import datetime
from pymongo import MongoClient

# Use MongoClient injection logic
client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017'))

def bulk_upload_configs(period: str, links: list):
    db = client['vpn_bot']
    configs_col = db['configs']

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    count = 0
    for i, link in enumerate(links):
        if not link.strip():
            continue

        config_name = f"Config_{period}_{timestamp}_{i}"
        conf_obj = {
            'name': config_name,
            'link': link.strip(),
            'code': f"code_{period}_{timestamp}_{i}",
            'used': False,
            'period': period
        }

        # Upsert by link to avoid duplicates
        configs_col.update_one({'link': link.strip()}, {'$set': conf_obj}, upsert=True)
        count += 1

    print(f"Uploaded {count} configs for period '{period}'.")
    return count

if __name__ == "__main__":
    print("Example usage of bulk_upload_configs:")
    print("bulk_upload_configs('1_month', ['vless://link1...', 'vless://link2...'])")