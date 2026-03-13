import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Add mock init script as specified in memory
        await page.add_init_script("""
            window.Telegram = {
                WebApp: {
                    initData: "mock_init_data_for_local",
                    openLink: function(url) { console.log("Opened link:", url); }
                }
            };
        """)

        # Get the absolute path to index.html
        file_path = f"file://{os.path.abspath('frontend/index.html')}"

        await page.goto(file_path)

        # Wait for the main content to be visible (which means app init worked and it loaded mock profile)
        await page.wait_for_selector("#main-content:not(.hidden)", state="visible", timeout=5000)

        # Verify text
        greeting = await page.inner_text("#user-greeting")
        assert "Hello, Local!" in greeting, f"Expected greeting to contain 'Hello, Local!', got {greeting}"

        balance = await page.inner_text("#user-balance")
        assert "1000 ₽" in balance, f"Expected balance to contain '1000 ₽', got {balance}"

        # Take a screenshot
        await page.screenshot(path="frontend_test.png")
        print("Frontend verification completed successfully. Screenshot saved to frontend_test.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
