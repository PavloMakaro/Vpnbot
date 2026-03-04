import unittest
import mongomock
import os
import json
import migrate_to_mongo

class TestMigrateToMongo(unittest.TestCase):
    def setUp(self):
        # Create dummy json files
        self.users_data = {
            "123": {"username": "testuser", "balance": 100}
        }
        self.configs_data = {
            "1_month": [{"link": "vless://test", "used": False, "name": "Config_1"}]
        }
        self.payments_data = {
            "pay123": {"amount": 50, "status": "pending"}
        }

        with open("users.json", "w") as f:
            json.dump(self.users_data, f)
        with open("configs.json", "w") as f:
            json.dump(self.configs_data, f)
        with open("payments.json", "w") as f:
            json.dump(self.payments_data, f)

        # Inject mock client into module
        self.mock_client = mongomock.MongoClient()
        migrate_to_mongo.client = self.mock_client

    def tearDown(self):
        if os.path.exists("users.json"):
            os.remove("users.json")
        if os.path.exists("configs.json"):
            os.remove("configs.json")
        if os.path.exists("payments.json"):
            os.remove("payments.json")

    def test_migrate_data(self):
        migrate_to_mongo.migrate_data()

        db = self.mock_client["vpn_bot"]

        users = list(db["users"].find())
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["_id"], "123")
        self.assertEqual(users[0]["balance"], 100)

        configs = list(db["configs"].find())
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0]["link"], "vless://test")
        self.assertEqual(configs[0]["period"], "1_month")

        payments = list(db["payments"].find())
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0]["_id"], "pay123")
        self.assertEqual(payments[0]["amount"], 50)

if __name__ == "__main__":
    unittest.main()
