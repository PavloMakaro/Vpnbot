import unittest
import mongomock
import admin_tool

class TestAdminTool(unittest.TestCase):
    def setUp(self):
        # Inject mongomock client directly
        self.mock_client = mongomock.MongoClient()
        admin_tool.client = self.mock_client
        self.db = self.mock_client[admin_tool.DB_NAME]

    def test_add_configs(self):
        period = "1_month"
        links = ["vless://link1", "vless://link2"]

        admin_tool.add_configs(period, links)

        configs = list(self.db.configs.find({"period": period}))
        self.assertEqual(len(configs), 2)

        links_in_db = [c["link"] for c in configs]
        self.assertIn("vless://link1", links_in_db)
        self.assertIn("vless://link2", links_in_db)

        # Test empty list
        admin_tool.add_configs("2_months", [])
        configs_empty = list(self.db.configs.find({"period": "2_months"}))
        self.assertEqual(len(configs_empty), 0)

if __name__ == '__main__':
    unittest.main()
