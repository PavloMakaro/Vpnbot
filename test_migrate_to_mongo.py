import unittest
import mongomock
import migrate_to_mongo

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Inject mock client
        self.mock_client = mongomock.MongoClient()
        migrate_to_mongo.client = self.mock_client
        self.db = self.mock_client["vpn_bot"]

    def test_migrate_users(self):
        users_data = {
            "123": {
                "username": "test1",
                "first_name": "Test One",
                "balance": 100
            },
            "456": {
                "username": "test2",
                "first_name": "Test Two",
                "balance": 50
            }
        }

        migrate_to_mongo.migrate_users(self.db, users_data)

        self.assertEqual(self.db.users.count_documents({}), 2)
        user1 = self.db.users.find_one({"_id": "123"})
        self.assertEqual(user1["username"], "test1")
        self.assertEqual(user1["balance"], 100)

    def test_migrate_configs(self):
        configs_data = {
            "1_month": [
                {
                    "name": "Config_1",
                    "link": "vless://test",
                    "code": "test",
                    "used": False
                }
            ]
        }

        migrate_to_mongo.migrate_configs(self.db, configs_data)

        self.assertEqual(self.db.configs.count_documents({}), 1)
        config1 = self.db.configs.find_one({"name": "Config_1"})
        self.assertEqual(config1["period"], "1_month")

    def test_migrate_payments(self):
        payments_data = {
            "pay123": {
                "user_id": "123",
                "amount": 500,
                "status": "pending"
            }
        }

        migrate_to_mongo.migrate_payments(self.db, payments_data)

        self.assertEqual(self.db.payments.count_documents({}), 1)
        payment1 = self.db.payments.find_one({"_id": "pay123"})
        self.assertEqual(payment1["amount"], 500)

if __name__ == '__main__':
    unittest.main()
