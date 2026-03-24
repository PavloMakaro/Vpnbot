import unittest
import mongomock
import json
import os
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Override the mongo client with mock
        self.mock_client = mongomock.MongoClient()
        migrate_to_mongo.client = self.mock_client

        # Prepare mock JSON data
        self.mock_users = {
            "123456": {"balance": 100, "username": "testuser"},
            "987654": {"balance": "50.5", "username": "user2"}
        }

        with open('users.json', 'w') as f:
            json.dump(self.mock_users, f)

    def tearDown(self):
        # Clean up files
        if os.path.exists('users.json'):
            os.remove('users.json')

    def test_migrate_data(self):
        # Run migration
        migrate_to_mongo.migrate_data()

        db = self.mock_client['vpn_bot']
        users_col = db['users']

        # Assertions
        self.assertEqual(users_col.count_documents({}), 2)

        user1 = users_col.find_one({'telegram_id': '123456'})
        self.assertIsNotNone(user1)
        self.assertEqual(user1['balance'], 100.0)

        user2 = users_col.find_one({'telegram_id': '987654'})
        self.assertIsNotNone(user2)
        self.assertEqual(user2['balance'], 50.5)

        # Explicit type check
        self.assertIsInstance(user1['telegram_id'], str)

if __name__ == '__main__':
    unittest.main()