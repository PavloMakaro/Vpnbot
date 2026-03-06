import unittest
import mongomock
import json
import os
import tempfile

# We import the functions to test
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Inject the mock client directly into the target module as specified in memory
        self.mock_client = mongomock.MongoClient()
        migrate_to_mongo.client = self.mock_client
        self.db = self.mock_client["vpn_bot"]

    def test_migrate_users(self):
        users_data = {
            "123": {
                "balance": 100,
                "subscription_end": "2023-12-31",
                "username": "testuser",
                "referrals_count": 5
            }
        }
        migrate_to_mongo.migrate_users(self.db, users_data)

        user = self.db.users.find_one({"_id": "123"})
        self.assertIsNotNone(user)
        self.assertEqual(user["balance"], 100.0)
        self.assertEqual(user["username"], "testuser")
        self.assertEqual(user["referrals_count"], 5)

    def test_migrate_configs(self):
        configs_data = {
            "1_month": [
                {
                    "name": "Config_1",
                    "link": "vless://test1",
                    "code": "code1",
                    "used": False
                }
            ]
        }
        migrate_to_mongo.migrate_configs(self.db, configs_data)

        config = self.db.configs.find_one({"link": "vless://test1"})
        self.assertIsNotNone(config)
        self.assertEqual(config["name"], "Config_1")
        self.assertEqual(config["period"], "1_month")
        self.assertFalse(config["used"])

    def test_migrate_payments(self):
        payments_data = {
            "pay_123": {
                "user_id": "123",
                "amount": 50,
                "status": "pending",
                "method": "yookassa_smart"
            }
        }
        migrate_to_mongo.migrate_payments(self.db, payments_data)

        payment = self.db.payments.find_one({"_id": "pay_123"})
        self.assertIsNotNone(payment)
        self.assertEqual(payment["user_id"], "123")
        self.assertEqual(payment["amount"], 50.0)
        self.assertEqual(payment["status"], "pending")

if __name__ == '__main__':
    unittest.main()