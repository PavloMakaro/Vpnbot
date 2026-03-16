import unittest
import mongomock
import os
import json
import tempfile
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Setup mock DB
        self.mock_client = mongomock.MongoClient()
        migrate_to_mongo.client = self.mock_client
        self.db = self.mock_client.vpn_bot

        # Create temp JSON files
        self.users_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.configs_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.payments_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')

        # Override file paths
        self.old_users = "users.json"
        self.old_configs = "configs.json"
        self.old_payments = "payments.json"

        # Patch the file names inside the module scope if needed,
        # but since we can't easily patch string literals, let's just create files in CWD temporarily
        json.dump({
            "12345": {
                "balance": 100,
                "subscription_end": "2024-01-01",
                "username": "testuser",
                "first_name": "Test",
                "referrals_count": 2,
                "used_configs": []
            }
        }, open("users.json", "w"))

        json.dump({
            "1_month": [
                {
                    "name": "Config_1",
                    "link": "vless://testlink",
                    "code": "code1",
                    "used": False
                }
            ]
        }, open("configs.json", "w"))

        json.dump({
            "pay_123": {
                "user_id": "12345",
                "amount": 50,
                "status": "pending",
                "method": "yookassa_smart",
                "timestamp": "2023-12-01",
                "type": "balance_topup",
                "payment_id": "pay_123"
            }
        }, open("payments.json", "w"))

    def tearDown(self):
        # Cleanup
        os.remove("users.json")
        os.remove("configs.json")
        os.remove("payments.json")

    def test_migrate_users(self):
        migrate_to_mongo.migrate_users(self.db)
        user = self.db.users.find_one({"_id": "12345"})
        self.assertIsNotNone(user)
        self.assertEqual(user["balance"], 100)
        self.assertEqual(user["username"], "testuser")

    def test_migrate_configs(self):
        migrate_to_mongo.migrate_configs(self.db)
        config = self.db.configs.find_one({"link": "vless://testlink"})
        self.assertIsNotNone(config)
        self.assertEqual(config["period"], "1_month")
        self.assertFalse(config["used"])

    def test_migrate_payments(self):
        migrate_to_mongo.migrate_payments(self.db)
        payment = self.db.payments.find_one({"_id": "pay_123"})
        self.assertIsNotNone(payment)
        self.assertEqual(payment["amount"], 50)
        self.assertEqual(payment["status"], "pending")

if __name__ == "__main__":
    unittest.main()