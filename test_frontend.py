from playwright.sync_api import sync_playwright
import unittest

class TestFrontend(unittest.TestCase):
    def test_frontend_loads(self):
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()

            # Mock Telegram WebApp SDK
            def mock_telegram_webapp(route):
                route.fulfill(
                    status=200,
                    content_type="application/javascript",
                    body="""
                    window.Telegram = {
                        WebApp: {
                            initDataUnsafe: {
                                user: { id: 12345, first_name: "TestUser" }
                            },
                            initData: "mocked_data",
                            themeParams: {},
                            ready: () => {},
                            expand: () => {},
                            showAlert: (msg) => console.log("ALERT:", msg)
                        }
                    };
                    """
                )
            context.route("https://telegram.org/js/telegram-web-app.js", mock_telegram_webapp)

            # Block Realm SDK to prevent initialization errors without credentials
            context.route("https://unpkg.com/realm-web@2.0.0/dist/bundle.iife.js", lambda route: route.abort())

            page = context.new_page()

            # Start HTTP server locally in bash: python -m http.server 8000 --directory frontend
            # Go to the local page
            response = page.goto("http://localhost:8000")

            # Assert page loaded successfully
            self.assertEqual(response.status, 200)

            # Check basic structure
            title = page.title()
            self.assertEqual(title, "VPN Bot")

            # Wait a bit
            page.wait_for_timeout(1000)

            # Ensure the dashboard view or loading view is present
            app_div = page.locator("#app")
            self.assertTrue(app_div.is_visible())

            # Take screenshot
            page.screenshot(path="frontend_test.png")

            browser.close()

if __name__ == '__main__':
    unittest.main()