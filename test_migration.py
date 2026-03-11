import unittest
import json
import os
import mongomock
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup mock db
        cls.mock_client = mongomock.MongoClient()
        cls.mock_db = cls.mock_client['vpn_bot']

        # Inject mock client into module
        migrate_to_mongo.client = cls.mock_client
        migrate_to_mongo.db = cls.mock_db

        # Create dummy json files
        cls.test_users = {
            "123": {"balance": 150, "subscription_end": "2024-12-31 23:59:59", "username": "test", "first_name": "Test User"}
        }
        cls.test_configs = {
            "1_month": [
                {"name": "Config_1", "link": "vless://test", "used": False}
            ]
        }
        cls.test_payments = {
            "pay1": {"user_id": "123", "amount": 50, "status": "confirmed"}
        }

        with open('users.json', 'w') as f:
            json.dump(cls.test_users, f)
        with open('configs.json', 'w') as f:
            json.dump(cls.test_configs, f)
        with open('payments.json', 'w') as f:
            json.dump(cls.test_payments, f)

    @classmethod
    def tearDownClass(cls):
        # Cleanup
        for file in ['users.json', 'configs.json', 'payments.json']:
            if os.path.exists(file):
                os.remove(file)

    def test_migrate_users(self):
        migrate_to_mongo.migrate_users()
        users = list(self.mock_db['users'].find())
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['_id'], "123")
        self.assertEqual(users[0]['balance'], 150.0)

    def test_migrate_configs(self):
        migrate_to_mongo.migrate_configs()
        configs = list(self.mock_db['configs'].find())
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0]['link'], "vless://test")

    def test_migrate_payments(self):
        migrate_to_mongo.migrate_payments()
        payments = list(self.mock_db['payments'].find())
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0]['_id'], "pay1")

if __name__ == '__main__':
    unittest.main()
