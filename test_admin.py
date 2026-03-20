import unittest
import mongomock
import os
import shutil
import admin_tool
from admin_tool import bulk_upload_configs

class TestAdminTool(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'test_data_admin'
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_file = os.path.join(self.test_dir, 'links.txt')

        with open(self.test_file, 'w') as f:
            f.write("vless://test1\nvless://test2\n\nvless://test1\n") # Includes duplicate and empty

        self.mock_client = mongomock.MongoClient()
        admin_tool.client = self.mock_client

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_bulk_upload(self):
        bulk_upload_configs("mongodb://fake", "1_month", self.test_file)

        db = self.mock_client.vpn_bot
        configs = list(db.configs.find())

        # 2 unique links should be inserted
        self.assertEqual(len(configs), 2)

        links = [c['link'] for c in configs]
        self.assertIn("vless://test1", links)
        self.assertIn("vless://test2", links)
        self.assertEqual(configs[0]['period'], "1_month")

if __name__ == '__main__':
    unittest.main()
