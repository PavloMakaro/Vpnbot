import unittest
import mongomock
import admin_tool
import sys

class TestAdminTool(unittest.TestCase):
    def setUp(self):
        self.mock_client = mongomock.MongoClient()
        admin_tool.client = self.mock_client
        self.db = admin_tool.get_db()

    def test_add_configs(self):
        admin_tool.add_configs("1_month", ["vless://link1", "vless://link2"])
        configs = list(self.db.configs.find({"period": "1_month"}))
        self.assertEqual(len(configs), 2)
        self.assertEqual(configs[0]['link'], "vless://link1")
        self.assertEqual(configs[1]['link'], "vless://link2")
        self.assertFalse(configs[0]['used'])
        self.assertIn('Config_1_month_', configs[0]['name'])

if __name__ == '__main__':
    unittest.main()
