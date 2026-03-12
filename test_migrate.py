import unittest
import mongomock
from datetime import datetime

import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Inject the mock client
        self.mock_client = mongomock.MongoClient()
        migrate_to_mongo.client = self.mock_client
        self.db = self.mock_client[migrate_to_mongo.DB_NAME]

    def test_migrate_users(self):
        users_data = {
            "123": {
                "username": "testuser",
                "balance": 100,
                "subscription_end": "2024-12-31 23:59:59"
            }
        }

        migrate_to_mongo.migrate_users(self.db, users_data)

        user = self.db.users.find_one({"_id": "123"})
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "testuser")
        self.assertEqual(user["balance"], 100)
        self.assertTrue(isinstance(user["subscription_end"], datetime))

    def test_migrate_configs(self):
        configs_data = {
            "1_month": [
                {"name": "test_config_1", "link": "vless://123", "code": "code1", "used": False}
            ]
        }

        migrate_to_mongo.migrate_configs(self.db, configs_data)

        config = self.db.configs.find_one({"link": "vless://123"})
        self.assertIsNotNone(config)
        self.assertEqual(config["name"], "test_config_1")
        self.assertEqual(config["period"], "1_month")
        self.assertFalse(config["used"])

if __name__ == '__main__':
    unittest.main()