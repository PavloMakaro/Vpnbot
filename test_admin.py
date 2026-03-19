import unittest
import mongomock
import admin_tool
import os

class TestAdminTool(unittest.TestCase):
    def setUp(self):
        self.client = mongomock.MongoClient()
        admin_tool.client = self.client
        self.db = self.client['vpn_bot']

    def test_upload_configs(self):
        period = "1_month"
        links = ["link1", "link2", "link3"]

        inserted = admin_tool.upload_configs(period, links)
        self.assertEqual(inserted, 3)

        configs = list(self.db.configs.find())
        self.assertEqual(len(configs), 3)

        c1 = self.db.configs.find_one({"_id": "link1"})
        self.assertIsNotNone(c1)
        self.assertEqual(c1['period'], "1_month")
        self.assertFalse(c1['used'])
        self.assertTrue(c1['name'].startswith("Config_1_month_"))

if __name__ == '__main__':
    unittest.main()