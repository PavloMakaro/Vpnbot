import unittest
import mongomock
import admin_tool
import os

class TestAdminTool(unittest.TestCase):
    def setUp(self):
        self.client = mongomock.MongoClient()
        self.db = self.client.vpn_bot

        self.test_file = "test_links.txt"
        with open(self.test_file, "w") as f:
            f.write("vless://link1\nvless://link2\n")

    def tearDown(self):
        try:
            os.remove(self.test_file)
        except FileNotFoundError:
            pass

    def test_upload_configs(self):
        with open(self.test_file, "r") as f:
            links = f.readlines()

        admin_tool.upload_configs(self.db, "1_month", links)

        configs = list(self.db.configs.find({"period": "1_month"}))
        self.assertEqual(len(configs), 2)

        self.assertEqual(configs[0]["link"], "vless://link1")
        self.assertFalse(configs[0]["used"])
        self.assertTrue(configs[0]["name"].startswith("Config_1_month_"))

if __name__ == '__main__':
    unittest.main()