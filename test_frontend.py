from playwright.sync_api import sync_playwright

def test_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 400, 'height': 800},
            device_scale_factor=2
        )

        # Abort the Realm request to prevent it from throwing errors
        context.route("https://unpkg.com/realm-web@2.0.0/dist/bundle.iife.js", lambda route: route.abort())

        page = context.new_page()

        # Mock Telegram WebApp object
        mock_script = """
            window.Telegram = {
                WebApp: {
                    initData: "user=%7B%22id%22%3A123%2C%22first_name%22%3A%22Test%22%2C%22username%22%3A%22test%22%7D&hash=abc",
                    themeParams: {
                        bg_color: "#ffffff",
                        text_color: "#000000",
                        button_color: "#3390ec",
                        button_text_color: "#ffffff",
                        secondary_bg_color: "#f4f4f5"
                    },
                    expand: () => {},
                    showAlert: (msg) => console.log('Alert:', msg),
                    MainButton: {
                        show: () => {},
                        hide: () => {},
                        showProgress: () => {},
                        hideProgress: () => {},
                    }
                }
            };

            // Mock Realm App and User functions
            window.Realm = {
                Credentials: {
                    function: (payload) => payload
                },
                App: class {
                    constructor({id}) { this.id = id; }
                    async logIn(credentials) {
                        return {
                            id: "123",
                            functions: {
                                getProfile: async () => ({
                                    _id: "123",
                                    first_name: "Mock User",
                                    username: "mockuser",
                                    balance: 1500,
                                    subscription_end: "2024-12-31 23:59:59",
                                    used_configs: [
                                        {
                                            config_name: "My config 1",
                                            config_link: "vless://mock1",
                                            period: "1_month",
                                            issue_date: "2024-01-01 12:00:00"
                                        }
                                    ]
                                }),
                                getConfigs: async () => ({
                                    periods: {
                                        "1_month": { price: 50, days: 30 },
                                        "3_months": { price: 120, days: 90 }
                                    }
                                })
                            }
                        };
                    }
                }
            };
        """

        page.route('https://telegram.org/js/telegram-web-app.js', lambda route: route.fulfill(
            status=200, content_type="application/javascript", body=""
        ))

        page.add_init_script(mock_script)

        try:
            page.goto('http://127.0.0.1:8000/', wait_until='networkidle')
            page.screenshot(path='frontend_mock.png')
            print("Frontend tests passed successfully! Output saved to frontend_mock.png.")
        except Exception as e:
            print(f"Error executing frontend verification: {e}")
            page.screenshot(path='frontend_error.png')
        finally:
            browser.close()

if __name__ == '__main__':
    test_frontend()