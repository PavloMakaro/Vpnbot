import os
import json
import unittest
import mongomock
from migrate_to_mongo import migrate_users, migrate_configs, migrate_payments

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Create dummy JSON data
        self.dummy_users = {
            "123": {
                "balance": 100,
                "subscription_end": "2023-12-01 10:00:00",
                "username": "testuser",
                "first_name": "Test",
                "used_configs": [{"config_name": "c1", "config_link": "http://c1"}]
            }
        }
        self.dummy_configs = {
            "1_month": [
                {"name": "test_cfg", "link": "http://link", "code": "123", "used": False}
            ]
        }
        self.dummy_payments = {
            "pay1": {
                "user_id": "123",
                "amount": 50,
                "status": "pending",
                "timestamp": "2023-11-01 10:00:00"
            }
        }

        # Setup mongomock
        self.client = mongomock.MongoClient()
        self.db = self.client.vpn_bot_db

    def test_migrate_users(self):
        migrate_users(self.db, self.dummy_users)
        users = list(self.db.users.find())
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['_id'], "123")
        self.assertEqual(users[0]['balance'], 100.0)
        self.assertIsNotNone(users[0].get('subscription_end_date'))
        self.assertEqual(len(users[0]['used_configs']), 1)

    def test_migrate_configs(self):
        migrate_configs(self.db, self.dummy_configs)
        configs = list(self.db.configs.find())
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0]['link'], "http://link")
        self.assertEqual(configs[0]['period'], "1_month")

    def test_migrate_payments(self):
        migrate_payments(self.db, self.dummy_payments)
        payments = list(self.db.payments.find())
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0]['_id'], "pay1")
        self.assertEqual(payments[0]['amount'], 50.0)

if __name__ == '__main__':
    unittest.main()
