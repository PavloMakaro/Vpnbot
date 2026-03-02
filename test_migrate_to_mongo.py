import unittest
import mongomock
from migrate_to_mongo import migrate_users, migrate_configs, migrate_payments

class TestMigration(unittest.TestCase):

    def setUp(self):
        self.client = mongomock.MongoClient()
        self.db = self.client['vpn_bot']

    def test_migrate_users(self):
        users_data = {
            "123": {"balance": 100, "username": "testuser"},
            "456": {"balance": 50, "subscription_end": "2024-01-01"}
        }
        migrate_users(self.db, users_data)

        users = list(self.db['users'].find())
        self.assertEqual(len(users), 2)

        user1 = self.db['users'].find_one({"_id": "123"})
        self.assertEqual(user1['balance'], 100)
        self.assertEqual(user1['username'], "testuser")

    def test_migrate_configs(self):
        configs_data = {
            "1_month": [{"name": "config1", "link": "vless://1", "used": False}],
            "2_months": [{"name": "config2", "link": "vless://2", "used": True}]
        }
        migrate_configs(self.db, configs_data)

        configs = list(self.db['configs'].find())
        self.assertEqual(len(configs), 2)

        c1 = self.db['configs'].find_one({"name": "config1"})
        self.assertEqual(c1['period'], "1_month")
        self.assertEqual(c1['used'], False)

    def test_migrate_payments(self):
        payments_data = {
            "pay1": {"user_id": "123", "amount": 50, "status": "pending"}
        }
        migrate_payments(self.db, payments_data)

        payments = list(self.db['payments'].find())
        self.assertEqual(len(payments), 1)

        p = self.db['payments'].find_one({"_id": "pay1"})
        self.assertEqual(p['amount'], 50)
        self.assertEqual(p['status'], "pending")

if __name__ == '__main__':
    unittest.main()
