import unittest
import mongomock
import admin_tool

class TestAdminTool(unittest.TestCase):
    def setUp(self):
        # Override client with mongomock
        self.client = mongomock.MongoClient()
        admin_tool.client = self.client
        self.db = self.client['vpn_bot']

    def test_bulk_upload_configs(self):
        links = ["http://link1.com", "http://link2.com", "  "] # One empty string
        period = "1_month"

        inserted_count = admin_tool.bulk_upload_configs(period, links)
        self.assertEqual(inserted_count, 2)

        configs = list(self.db['configs'].find())
        self.assertEqual(len(configs), 2)
        self.assertEqual(configs[0]['period'], period)
        self.assertIn("Config_", configs[0]['name'])
        self.assertEqual(configs[0]['link'], "http://link1.com")
        self.assertFalse(configs[0]['used'])

    def test_empty_upload(self):
        inserted_count = admin_tool.bulk_upload_configs("1_month", [])
        self.assertEqual(inserted_count, 0)

        configs = list(self.db['configs'].find())
        self.assertEqual(len(configs), 0)

if __name__ == '__main__':
    unittest.main()
