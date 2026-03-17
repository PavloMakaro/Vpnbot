import unittest
import mongomock
import admin_tool

class TestAdminTool(unittest.TestCase):
    def setUp(self):
        # Setup mock mongo client
        self.client = mongomock.MongoClient()
        # Inject mock client into module
        admin_tool.client = self.client

    def tearDown(self):
        admin_tool.client = None

    def test_upload_configs(self):
        # Run upload
        period = "1_month"
        links = ["vless://test1", "vless://test2"]
        admin_tool.upload_configs(period, links)

        db = self.client.vpn_bot
        configs = list(db.configs.find())

        self.assertEqual(len(configs), 2)

        # Verify first config
        config1 = db.configs.find_one({"link": "vless://test1"})
        self.assertIsNotNone(config1)
        self.assertEqual(config1["period"], "1_month")
        self.assertFalse(config1["used"])
        self.assertTrue(config1["name"].startswith("Config_"))

        # Verify second config
        config2 = db.configs.find_one({"link": "vless://test2"})
        self.assertIsNotNone(config2)

    def test_upload_duplicate_configs(self):
        # Run upload
        period = "1_month"
        links = ["vless://test1", "vless://test1"]
        admin_tool.upload_configs(period, links)

        db = self.client.vpn_bot
        configs = list(db.configs.find())

        # Should only be 1 config since it handles duplicates gracefully
        self.assertEqual(len(configs), 1)

if __name__ == '__main__':
    unittest.main()
