from playwright.sync_api import sync_playwright
import time

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Emulate a mobile device
        context = browser.new_context(
            viewport={'width': 375, 'height': 667},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        )
        page = context.new_page()

        # Navigate to the app (mock mode should trigger)
        page.goto("http://localhost:8080/index.html")

        # Wait for loading animation to finish (simulated delay in app.js is 800ms)
        time.sleep(2)

        # Take screenshot of Home View
        page.screenshot(path="frontend_home.png")
        print("Captured Home View")

        # Navigate to Shop
        # "Buy VPN" button contains text "Buy VPN"
        # The selector "text=Buy VPN" might find the span inside the button.
        page.locator("button:has-text('Buy VPN')").click()
        time.sleep(1)
        page.screenshot(path="frontend_shop.png")
        print("Captured Shop View")

        # Go back from Shop
        # The back button is an icon button inside #shop-view
        # It's the first button in that view.
        page.locator("#shop-view button").first.click()
        time.sleep(1)

        # Navigate to Configs
        page.locator("button:has-text('My Configs')").click()
        time.sleep(1)
        page.screenshot(path="frontend_configs.png")
        print("Captured Configs View")

        browser.close()

if __name__ == "__main__":
    verify_frontend()
