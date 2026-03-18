import unittest
import mongomock
import json
import os
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Override client with mongomock
        self.client = mongomock.MongoClient()
        migrate_to_mongo.client = self.client

        # Create temporary JSON files
        with open('users.json', 'w') as f:
            json.dump({'12345': {'balance': 100, 'username': 'testuser'}}, f)

        with open('configs.json', 'w') as f:
            json.dump({'1_month': [{'link': 'http://test', 'name': 'c1', 'code': 'xyz', 'used': False}]}, f)

        with open('payments.json', 'w') as f:
            json.dump({'pay_1': {'amount': 50, 'status': 'confirmed', 'user_id': '12345'}}, f)

    def tearDown(self):
        # Cleanup JSON files
        for f in ['users.json', 'configs.json', 'payments.json']:
            if os.path.exists(f):
                os.remove(f)

    def test_migration(self):
        migrate_to_mongo.migrate_data()

        db = self.client['vpn_bot']

        users = list(db['users'].find())
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['_id'], '12345')
        self.assertEqual(users[0]['balance'], 100)

        configs = list(db['configs'].find())
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0]['period'], '1_month')

        payments = list(db['payments'].find())
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0]['_id'], 'pay_1')
        self.assertEqual(payments[0]['status'], 'confirmed')

if __name__ == '__main__':
    unittest.main()
