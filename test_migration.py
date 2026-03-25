import unittest
import mongomock
import json
import os
import sys

# Add current directory to path so we can import the module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Create a mock MongoDB client
        self.mock_client = mongomock.MongoClient()

        # Create temporary JSON files for testing
        self.users_data = {
            "123456789": {
                "balance": 100,
                "username": "testuser",
                "first_name": "Test"
            }
        }
        self.configs_data = {
            "1_month": [
                {
                    "name": "Config_1_month_1",
                    "link": "vless://testlink",
                    "code": "code_1_month_1",
                    "used": False
                }
            ]
        }
        self.payments_data = {
            "pay_123": {
                "user_id": 123456789,
                "amount": 50,
                "status": "pending"
            }
        }

        with open('users.json', 'w') as f:
            json.dump(self.users_data, f)
        with open('configs.json', 'w') as f:
            json.dump(self.configs_data, f)
        with open('payments.json', 'w') as f:
            json.dump(self.payments_data, f)

    def tearDown(self):
        # Clean up temporary JSON files
        if os.path.exists('users.json'):
            os.remove('users.json')
        if os.path.exists('configs.json'):
            os.remove('configs.json')
        if os.path.exists('payments.json'):
            os.remove('payments.json')

    def test_migration(self):
        # Inject the mock client
        migrate_to_mongo.MONGO_DB_NAME = "vpn_bot"
        migrate_to_mongo.migrate_data(client=self.mock_client)

        db = self.mock_client["vpn_bot"]

        # Check users
        users = list(db["users"].find())
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["telegram_id"], "123456789") # Ensure cast to string
        self.assertEqual(users[0]["username"], "testuser")

        # Check configs
        configs = list(db["configs"].find())
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0]["period"], "1_month")
        self.assertEqual(configs[0]["link"], "vless://testlink")

        # Check payments
        payments = list(db["payments"].find())
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0]["_id"], "pay_123")
        self.assertEqual(payments[0]["user_id"], "123456789")

if __name__ == '__main__':
    unittest.main()
