const { test, expect } = require('@playwright/test');

test.describe('Frontend Logic Mocks', () => {
    test('UI renders without crashing when mocked', async ({ page }) => {
        // Mock Telegram WebApp and Realm App
        await page.addInitScript(() => {
            window.Telegram = {
                WebApp: {
                    expand: () => {},
                    ready: () => {},
                    MainButton: { hide: () => {}, show: () => {} },
                    BackButton: { hide: () => {}, show: () => {}, onClick: () => {} },
                    initData: 'mock_data',
                    showAlert: (msg) => console.log('ALERT:', msg),
                    showPopup: (opt) => console.log('POPUP:', opt.title),
                    showConfirm: (msg, cb) => cb(true)
                }
            };

            window.Realm = {
                Credentials: {
                    function: (args) => args
                },
                App: class {
                    constructor({id}) { this.id = id; }
                    async logIn() {
                        return {
                            id: 'mock_user_123',
                            functions: {
                                getProfile: async () => ({
                                    first_name: 'Test',
                                    username: 'test_mock',
                                    balance: 100,
                                    referrals_count: 5,
                                    daysLeft: 10,
                                    subscriptionEndDateFormatted: '01.01.2025',
                                    used_configs: []
                                }),
                                getConfigs: async () => ({
                                    '1_month': { price: 50, days: 30 }
                                })
                            }
                        };
                    }
                }
            };
        });

        // Load the frontend index
        await page.goto(`file://${process.cwd()}/frontend/index.html`);

        // Wait for profile view to become active (meaning loadProfile finished)
        await page.waitForSelector('#profileView.active');

        // Check if values were updated correctly by the script
        const balanceText = await page.locator('#userBalance').innerText();
        expect(balanceText).toBe('100 ₽');

        const usernameText = await page.locator('#userUsername').innerText();
        expect(usernameText).toBe('@test_mock');

        const daysLeftText = await page.locator('#subEndDate').innerText();
        expect(daysLeftText).toContain('осталось 10 дн.');
    });
});
