import asyncio
import os
import subprocess
import time
from playwright.async_api import async_playwright

async def run():
    # Start local HTTP server for frontend
    server_process = subprocess.Popen(
        ["python", "-m", "http.server", "8000", "--directory", "frontend"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Wait for server to start
    time.sleep(2)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()

        # Abort realm-web network requests to prevent initialization errors since we don't have a real Atlas App running
        await context.route("https://unpkg.com/realm-web@2.0.0/dist/bundle.iife.js", lambda route: route.abort())

        page = await context.new_page()

        # Mock window.Telegram.WebApp
        await page.add_init_script("""
            window.Telegram = {
                WebApp: {
                    expand: function() {},
                    close: function() {},
                    initData: "query_id=AAHdF6kqAAAAAN0XqSpVxxx&user=%7B%22id%22%3A123456789%2C%22first_name%22%3A%22Test%22%2C%22last_name%22%3A%22User%22%2C%22username%22%3A%22testuser%22%2C%22language_code%22%3A%22ru%22%2C%22allows_write_to_pm%22%3Atrue%7D&auth_date=1672531200&hash=mockhash",
                    initDataUnsafe: {
                        user: {
                            id: 123456789,
                            first_name: "Test",
                            last_name: "User",
                            username: "testuser"
                        }
                    },
                    HapticFeedback: {
                        impactOccurred: function(style) {},
                        notificationOccurred: function(type) {},
                        selectionChanged: function() {}
                    },
                    openLink: function(url) {}
                }
            };

            // Mock Realm SDK globally
            window.Realm = {
                App: class {
                    constructor(config) {
                        this.id = config.id;
                        this.currentUser = {
                            functions: {
                                getProfile: async () => ({
                                    first_name: "Test",
                                    balance: 150,
                                    subscription_end: new Date(Date.now() + 864000000).toISOString(),
                                    used_configs: [
                                        {
                                            config_name: "Config_1",
                                            config_link: "vless://test",
                                            period: "1_month",
                                            issue_date: new Date().toISOString()
                                        }
                                    ]
                                }),
                                getConfigs: async () => ({
                                    '1_month': { price: 50, title: '30 дней' }
                                }),
                                checkPendingPayments: async () => ({ success: true, updated: 0 })
                            }
                        };
                    }
                    async logIn(credentials) {
                        return this.currentUser;
                    }
                },
                Credentials: {
                    function: (payload) => payload
                }
            };
        """)

        try:
            await page.goto("http://localhost:8000/index.html")

            # Wait for app to be visible
            await page.wait_for_selector("#app", state="visible", timeout=10000)

            # Take screenshot
            await page.screenshot(path="frontend_screenshot.png", full_page=True)
            print("Frontend verification successful. Screenshot saved to frontend_screenshot.png")

        except Exception as e:
            print(f"Frontend verification failed: {e}")
            await page.screenshot(path="frontend_error.png")

        finally:
            await browser.close()
            server_process.terminate()

if __name__ == "__main__":
    asyncio.run(run())
