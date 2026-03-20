import unittest
import mongomock
import json
import os
import shutil
from migrate_to_mongo import get_client, run_migration
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'test_data'
        os.makedirs(self.test_dir, exist_ok=True)

        # Create mock json files
        self.users = {
            "123": {
                "balance": 100,
                "username": "testuser",
                "used_configs": []
            }
        }
        self.configs = {
            "1_month": [
                {"name": "test_conf", "link": "vless://test", "used": False}
            ]
        }

        with open(os.path.join(self.test_dir, 'users.json'), 'w') as f:
            json.dump(self.users, f)
        with open(os.path.join(self.test_dir, 'configs.json'), 'w') as f:
            json.dump(self.configs, f)

        # Inject mongomock client
        self.mock_client = mongomock.MongoClient()
        migrate_to_mongo.client = self.mock_client

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_migration(self):
        run_migration("mongodb://fake", self.test_dir)
        db = self.mock_client.vpn_bot

        user = db.users.find_one({"_id": "123"})
        self.assertIsNotNone(user)
        self.assertEqual(user['balance'], 100)
        self.assertEqual(user['username'], "testuser")

        config = db.configs.find_one({"link": "vless://test"})
        self.assertIsNotNone(config)
        self.assertEqual(config['period'], "1_month")

if __name__ == '__main__':
    unittest.main()
