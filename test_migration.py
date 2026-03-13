import unittest
import mongomock
import json
import os
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        self.mock_client = mongomock.MongoClient()
        migrate_to_mongo.client = self.mock_client
        self.db = migrate_to_mongo.get_db()

        # Create dummy json files for testing
        with open('users.json', 'w') as f:
            json.dump({"123": {"username": "testuser", "balance": 100}}, f)
        with open('configs.json', 'w') as f:
            json.dump({"1_month": [{"link": "vless://test", "name": "Config1"}]}, f)
        with open('payments.json', 'w') as f:
            json.dump({"pay1": {"amount": 50, "status": "pending"}}, f)

    def tearDown(self):
        for f in ['users.json', 'configs.json', 'payments.json']:
            if os.path.exists(f):
                os.remove(f)

    def test_migrate_users(self):
        migrate_to_mongo.migrate_users(self.db)
        user = self.db.users.find_one({"_id": "123"})
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "testuser")

    def test_migrate_configs(self):
        migrate_to_mongo.migrate_configs(self.db)
        config = self.db.configs.find_one({"link": "vless://test"})
        self.assertIsNotNone(config)
        self.assertEqual(config['period'], "1_month")

    def test_migrate_payments(self):
        migrate_to_mongo.migrate_payments(self.db)
        payment = self.db.payments.find_one({"payment_id": "pay1"})
        self.assertIsNotNone(payment)
        self.assertEqual(payment['amount'], 50)

if __name__ == '__main__':
    unittest.main()
