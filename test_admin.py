import unittest
import mongomock
import os
import sys

# Add current directory to path so we can import the module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import admin_tool

class TestAdmin(unittest.TestCase):
    def setUp(self):
        # Create a mock MongoDB client
        self.mock_client = mongomock.MongoClient()
        admin_tool.MongoClient = lambda uri: self.mock_client
        admin_tool.MONGO_DB_NAME = "vpn_bot"

        # Create a dummy config file
        self.test_file = "test_configs.txt"
        with open(self.test_file, 'w') as f:
            f.write("vless://link1\n")
            f.write("vless://link2\n")

    def tearDown(self):
        # Clean up the dummy config file
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_admin_upload(self):
        # Mock sys.argv to simulate command line arguments
        sys.argv = ['admin_tool.py', '1_month', self.test_file]

        # Run main function
        admin_tool.main()

        # Verify database
        db = self.mock_client["vpn_bot"]
        configs = list(db["configs"].find())

        self.assertEqual(len(configs), 2)
        self.assertEqual(configs[0]["link"], "vless://link1")
        self.assertEqual(configs[1]["link"], "vless://link2")
        self.assertEqual(configs[0]["period"], "1_month")
        self.assertIn("Config_1_month_", configs[0]["name"])
        self.assertFalse(configs[0]["used"])

if __name__ == '__main__':
    unittest.main()
