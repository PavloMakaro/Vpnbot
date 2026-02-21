from playwright.sync_api import sync_playwright
import time
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Inject mock Telegram WebApp object
        page.add_init_script("""
            window.Telegram = {
                WebApp: {
                    expand: () => console.log('Expanded'),
                    initData: 'query_id=...',
                    initDataUnsafe: {
                        user: {
                            id: 123456789,
                            first_name: 'Test User',
                            username: 'test_user'
                        }
                    },
                    themeParams: {
                        bg_color: '#111827',
                        text_color: '#ffffff'
                    },
                    openLink: (url) => console.log('Opening link:', url)
                }
            };
        """)

        page.goto("http://localhost:8000/index.html")

        # Wait for user name to appear (populated by JS)
        page.wait_for_selector("#user-name")

        # Take screenshot of the "Buy VPN" tab (default)
        if not os.path.exists("verification"):
            os.makedirs("verification")
        page.screenshot(path="verification/tab_buy.png")
        print("Screenshot of Buy Tab taken")

        # Click "Top Up" tab
        page.click("button[onclick=\"switchTab('topup')\"]")
        time.sleep(0.5) # Wait for transition
        page.screenshot(path="verification/tab_topup.png")
        print("Screenshot of Top Up Tab taken")

        # Click "Configs" tab
        page.click("button[onclick=\"switchTab('configs')\"]")
        time.sleep(0.5)
        page.screenshot(path="verification/tab_configs.png")
        print("Screenshot of Configs Tab taken")

        # Click "Profile" tab
        page.click("button[onclick=\"switchTab('profile')\"]")
        time.sleep(0.5)
        page.screenshot(path="verification/tab_profile.png")
        print("Screenshot of Profile Tab taken")

        # Open Modal
        page.click("button[onclick=\"switchTab('buy')\"]")
        time.sleep(0.5)
        page.click("div[onclick=\"selectPlan('1_month', 50)\"]")
        time.sleep(0.5)
        page.screenshot(path="verification/modal_confirm.png")
        print("Screenshot of Modal taken")

        browser.close()

if __name__ == "__main__":
    run()
