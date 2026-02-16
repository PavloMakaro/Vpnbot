from playwright.sync_api import sync_playwright
import time
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the local server (assuming started)
        page.goto("http://localhost:8080")

        # Wait a bit for JS to run
        time.sleep(2)

        # Check if loading screen is present (it should be, or an alert)
        # Note: alert dialogs might block execution if not handled.
        # But here we just want to see the page state.

        # Take screenshot
        page.screenshot(path="verification/frontend_load.png")

        browser.close()

if __name__ == "__main__":
    run()
