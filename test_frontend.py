import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Abort the Realm SDK network request so it fails gracefully without valid credentials
        await context.route("https://unpkg.com/realm-web@2.0.0/dist/bundle.iife.js", lambda route: route.abort())

        # Mock the Telegram WebApp object
        await page.route("https://telegram.org/js/telegram-web-app.js", lambda route: route.fulfill(
            status=200,
            content_type="application/javascript",
            body="""
            window.Telegram = {
                WebApp: {
                    ready: () => {},
                    expand: () => {},
                    initData: "user=%7B%22id%22%3A123%2C%22first_name%22%3A%22Test%22%2C%22last_name%22%3A%22User%22%2C%22username%22%3A%22testuser%22%2C%22language_code%22%3A%22en%22%7D",
                    initDataUnsafe: {
                        user: {
                            id: 123,
                            first_name: "Test",
                            last_name: "User",
                            username: "testuser",
                            language_code: "en"
                        }
                    }
                }
            };
            """
        ))

        print("Navigating to http://localhost:8000")
        await page.goto("http://localhost:8000")

        await page.wait_for_timeout(2000)

        # Check if the loading div is present
        loading_div = await page.locator("#loading").is_visible()
        print(f"Loading div visible: {loading_div}")

        # Check if Realm error occurred since we blocked the SDK
        if loading_div:
             loading_text = await page.locator("#loading").inner_text()
             print(f"Loading text: {loading_text}")

        await page.screenshot(path="frontend_test.png")
        print("Screenshot saved to frontend_test.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())