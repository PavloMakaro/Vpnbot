import unittest
import mongomock
import admin_tool
import os

class TestAdmin(unittest.TestCase):
    def setUp(self):
        # Override the mongo client with mock
        self.mock_client = mongomock.MongoClient()
        admin_tool.client = self.mock_client

    def test_bulk_upload_configs(self):
        links = ["vless://link1", "vless://link2", "   "]

        # Test function
        count = admin_tool.bulk_upload_configs("1_month", links)
        self.assertEqual(count, 2)

        db = self.mock_client['vpn_bot']
        configs_col = db['configs']

        # Assertions
        self.assertEqual(configs_col.count_documents({}), 2)

        config1 = configs_col.find_one({'link': 'vless://link1'})
        self.assertIsNotNone(config1)
        self.assertEqual(config1['period'], "1_month")
        self.assertFalse(config1['used'])
        self.assertTrue(config1['name'].startswith("Config_1_month_"))

        config2 = configs_col.find_one({'link': 'vless://link2'})
        self.assertIsNotNone(config2)

if __name__ == '__main__':
    unittest.main()