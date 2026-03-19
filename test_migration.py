import unittest
import mongomock
import migrate_to_mongo
import json
import os

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Create mock data files
        self.mock_users = {
            "12345": {"username": "user1", "balance": 100}
        }
        self.mock_configs = {
            "1_month": [{"name": "C1", "link": "link1"}],
            "2_months": [{"name": "C2", "link": "link2"}]
        }
        self.mock_payments = {
            "pay1": {"user_id": "12345", "amount": 50, "status": "pending"}
        }

        with open('users.json', 'w') as f: json.dump(self.mock_users, f)
        with open('configs.json', 'w') as f: json.dump(self.mock_configs, f)
        with open('payments.json', 'w') as f: json.dump(self.mock_payments, f)

        # Inject mongomock client
        self.client = mongomock.MongoClient()
        migrate_to_mongo.client = self.client

    def tearDown(self):
        for f in ['users.json', 'configs.json', 'payments.json']:
            if os.path.exists(f): os.remove(f)

    def test_migration(self):
        migrate_to_mongo.migrate()

        db = self.client['vpn_bot']

        # Check users
        user = db.users.find_one({"_id": "12345"})
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "user1")

        # Check configs
        configs = list(db.configs.find())
        self.assertEqual(len(configs), 2)
        c1 = db.configs.find_one({"_id": "link1"})
        self.assertEqual(c1['period'], "1_month")

        # Check payments
        pay = db.payments.find_one({"_id": "pay1"})
        self.assertIsNotNone(pay)
        self.assertEqual(pay['amount'], 50)

if __name__ == '__main__':
    unittest.main()