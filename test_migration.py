import unittest
import mongomock
import json
import os
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        self.client = mongomock.MongoClient()
        self.db = self.client.vpn_bot

        # Create dummy JSON files
        self.test_dir = "test_data"
        os.makedirs(self.test_dir, exist_ok=True)

        with open(f"{self.test_dir}/users.json", "w") as f:
            json.dump({"123": {"username": "testuser", "balance": 100}}, f)

        with open(f"{self.test_dir}/configs.json", "w") as f:
            json.dump({"1_month": [{"link": "vless://test", "used": False}]}, f)

        with open(f"{self.test_dir}/payments.json", "w") as f:
            json.dump({"pay123": {"user_id": "123", "amount": 50}}, f)

    def tearDown(self):
        # Cleanup dummy JSON files
        for file in ["users.json", "configs.json", "payments.json"]:
            try:
                os.remove(f"{self.test_dir}/{file}")
            except FileNotFoundError:
                pass
        os.rmdir(self.test_dir)

    def test_migrate_users(self):
        migrate_to_mongo.migrate_users(self.db, f"{self.test_dir}/users.json")
        user = self.db.users.find_one({"telegram_id": "123"})
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "testuser")
        self.assertEqual(user["balance"], 100)

    def test_migrate_configs(self):
        migrate_to_mongo.migrate_configs(self.db, f"{self.test_dir}/configs.json")
        config = self.db.configs.find_one({"link": "vless://test"})
        self.assertIsNotNone(config)
        self.assertEqual(config["period"], "1_month")
        self.assertFalse(config["used"])

    def test_migrate_payments(self):
        migrate_to_mongo.migrate_payments(self.db, f"{self.test_dir}/payments.json")
        payment = self.db.payments.find_one({"payment_id": "pay123"})
        self.assertIsNotNone(payment)
        self.assertEqual(payment["user_id"], "123")
        self.assertEqual(payment["amount"], 50)

if __name__ == '__main__':
    unittest.main()