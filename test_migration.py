import unittest
import mongomock
import os
import json
import tempfile
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Setup mock mongo client
        self.client = mongomock.MongoClient()
        # Inject mock client into module
        migrate_to_mongo.client = self.client

        # Setup temporary test data files
        self.test_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir.name)

        # Dummy users data
        users_data = {
            "123": {"balance": 100, "username": "testuser"},
            "456": {"balance": 50, "username": "testuser2"}
        }
        with open("users.json", "w") as f:
            json.dump(users_data, f)

        # Dummy configs data
        configs_data = {
            "1_month": [
                {"name": "config1", "link": "vless://1", "used": False},
                {"name": "config2", "link": "vless://2", "used": True}
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(configs_data, f)

        # Dummy payments data
        payments_data = {
            "pay1": {"amount": 100, "status": "pending"},
            "pay2": {"amount": 200, "status": "confirmed"}
        }
        with open("payments.json", "w") as f:
            json.dump(payments_data, f)

    def tearDown(self):
        # Restore cwd and clean up
        os.chdir(self.original_cwd)
        self.test_dir.cleanup()
        migrate_to_mongo.client = None

    def test_migration(self):
        # Run migration
        migrate_to_mongo.migrate()

        db = self.client.vpn_bot

        # Verify users
        users = list(db.users.find())
        self.assertEqual(len(users), 2)
        user_123 = db.users.find_one({"_id": "123"})
        self.assertEqual(user_123["username"], "testuser")
        self.assertEqual(user_123["balance"], 100)

        # Verify configs
        configs = list(db.configs.find())
        self.assertEqual(len(configs), 2)
        config1 = db.configs.find_one({"link": "vless://1"})
        self.assertEqual(config1["period"], "1_month")
        self.assertFalse(config1["used"])

        # Verify payments
        payments = list(db.payments.find())
        self.assertEqual(len(payments), 2)
        pay1 = db.payments.find_one({"_id": "pay1"})
        self.assertEqual(pay1["status"], "pending")

if __name__ == '__main__':
    unittest.main()
