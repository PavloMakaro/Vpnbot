import unittest
import json
import os
import mongomock
from pymongo import MongoClient

# Make the migration script testable by separating concerns or patching the collections
from migrate_to_mongo import migrate_users, migrate_configs, migrate_payments

class TestMigration(unittest.TestCase):
    @mongomock.patch(servers=(('localhost', 27017),))
    def test_migrate_users(self):
        # Create test users.json
        test_users = {
            "123": {
                "username": "testuser",
                "balance": 100
            }
        }
        with open('users.json', 'w') as f:
            json.dump(test_users, f)

        # For the test to work correctly with mongomock, we need to inject the mongomock client
        import migrate_to_mongo

        client = mongomock.MongoClient()
        # Override the real collections with the mocked ones
        migrate_to_mongo.client = client
        migrate_to_mongo.db = client['vpn']
        migrate_to_mongo.users_col = migrate_to_mongo.db['users']
        migrate_to_mongo.configs_col = migrate_to_mongo.db['configs']
        migrate_to_mongo.payments_col = migrate_to_mongo.db['payments']

        migrate_to_mongo.migrate_users()

        users_col = migrate_to_mongo.db['users']

        user = users_col.find_one({"_id": "123"})
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "testuser")
        self.assertEqual(user['balance'], 100.0)

        os.remove('users.json')

if __name__ == '__main__':
    unittest.main()