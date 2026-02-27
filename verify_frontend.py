
from playwright.sync_api import sync_playwright
import os

def run_frontend_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Mock window.Telegram.WebApp and Realm
        page.add_init_script("""
            window.Telegram = {
                WebApp: {
                    initData: "query_id=AAH...",
                    expand: () => {},
                    enableClosingConfirmation: () => {},
                    openLink: (url) => console.log('Opening link:', url),
                    onEvent: () => {},
                    offEvent: () => {},
                    sendData: () => {},
                    ready: () => {},
                    MainButton: { text: '', color: '', textColor: '', isVisible: false, isActive: true, show: () => {}, hide: () => {} },
                    BackButton: { isVisible: false, show: () => {}, hide: () => {} }
                }
            };

            // Mock Realm
            window.Realm = {
                App: class {
                    constructor(config) { this.id = config.id; }
                    logIn() {
                        return Promise.resolve({
                            id: "test-user-id",
                            functions: {
                                getProfile: () => Promise.resolve({
                                    username: "test_user",
                                    balance: 150,
                                    subscription_end: new Date(Date.now() + 86400000 * 5).toISOString(), // 5 days left
                                    referrals_count: 2,
                                    used_configs: [
                                        { config_name: "Config_1", issue_date: new Date().toISOString(), config_link: "vless://..." }
                                    ]
                                }),
                                getConfigs: () => Promise.resolve({
                                    '1_month': { price: 50, days: 30 },
                                    '2_months': { price: 90, days: 60 }
                                }),
                                buySubscription: () => Promise.resolve({ success: true }),
                                createPayment: () => Promise.resolve({ confirmation_url: "https://yookassa..." }),
                                checkPayment: () => Promise.resolve({ status: "pending" })
                            }
                        });
                    }
                },
                Credentials: {
                    function: (payload) => payload
                }
            };
        """)

        # Load the local HTML file
        # Ensure we are in the root directory or adjust path
        cwd = os.getcwd()
        page.goto(f"file://{cwd}/frontend/index.html")

        # Wait for profile to load (username to appear)
        page.wait_for_selector("#username", state="visible")
        page.wait_for_function("document.getElementById('username').innerText !== '...'")

        # Take screenshot
        os.makedirs("verification", exist_ok=True)
        screenshot_path = os.path.join("verification", "frontend_verification.png")
        page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()

if __name__ == "__main__":
    run_frontend_test()
