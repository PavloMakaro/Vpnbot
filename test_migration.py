import unittest
import mongomock
import json
import os

# Import the module to test
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Inject mongomock client directly
        self.mock_client = mongomock.MongoClient()
        migrate_to_mongo.client = self.mock_client
        self.db = self.mock_client[migrate_to_mongo.DB_NAME]

    def test_migrate_users(self):
        users_data = {
            "12345": {
                "balance": 100,
                "username": "testuser",
                "first_name": "Test",
                "used_configs": []
            }
        }
        migrate_to_mongo.migrate_users(self.db, users_data)

        user = self.db.users.find_one({"telegram_id": 12345})
        self.assertIsNotNone(user)
        self.assertEqual(user["balance"], 100)
        self.assertEqual(user["username"], "testuser")

    def test_migrate_configs(self):
        configs_data = {
            "1_month": [
                {
                    "name": "Config_1",
                    "link": "vless://test",
                    "code": "code_1",
                    "used": False
                }
            ]
        }
        migrate_to_mongo.migrate_configs(self.db, configs_data)

        config = self.db.configs.find_one({"link": "vless://test"})
        self.assertIsNotNone(config)
        self.assertEqual(config["period"], "1_month")
        self.assertFalse(config["used"])

    def test_migrate_payments(self):
        payments_data = {
            "pay_123": {
                "user_id": "12345",
                "amount": 500,
                "status": "pending"
            }
        }
        migrate_to_mongo.migrate_payments(self.db, payments_data)

        payment = self.db.payments.find_one({"payment_id": "pay_123"})
        self.assertIsNotNone(payment)
        self.assertEqual(payment["user_id"], "12345")
        self.assertEqual(payment["amount"], 500)

if __name__ == '__main__':
    unittest.main()
