from playwright.sync_api import sync_playwright
import os

def run(playwright):
    browser = playwright.chromium.launch()
    page = browser.new_page()

    # Get absolute path to index.html
    cwd = os.getcwd()
    file_path = f"file://{cwd}/frontend/index.html"

    print(f"Navigating to {file_path}")
    page.goto(file_path)

    # Wait for the loading screen to appear (it's visible by default)
    page.wait_for_selector("#loading-screen")

    # Take a screenshot of the loading state
    page.screenshot(path="verification/frontend_loading.png")
    print("Screenshot saved to verification/frontend_loading.png")

    # Now let's try to inspect if the main content structure exists (hidden)
    content = page.content()
    if "VPN Mini App" in content:
        print("Title verification passed")

    if "id=\"main-content\"" in content:
        print("Main content container found")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
