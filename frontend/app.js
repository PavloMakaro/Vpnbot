const REALM_APP_ID = "YOUR_REALM_APP_ID"; // Replace with actual Realm App ID

class VPNApp {
    constructor() {
        this.realmApp = new Realm.App({ id: REALM_APP_ID });
        this.currentUser = null;
        this.profile = null;
        this.configs = null;
        this.selectedTopUpAmount = 0;
        this.tg = window.Telegram.WebApp;
        this.tg.expand();

        this.init();
    }

    async init() {
        this.showLoading(true);
        try {
            await this.authenticate();
            await this.loadData();

            // Check for pending payments on load
            if (this.currentUser) {
                await this.currentUser.functions.checkPendingPayments();
                await this.loadData(); // Reload profile if balance updated
            }

            this.showView('profile');
        } catch (error) {
            console.error("Initialization error:", error);
            this.showError("Failed to initialize app. Please try again later.");
        } finally {
            this.showLoading(false);
        }
    }

    async authenticate() {
        const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:';

        let credentials;

        if (isLocalhost || !this.tg.initData) {
            console.log("Running locally or without Telegram context. Using mock auth.");
            // Mock authentication for local development
            credentials = Realm.Credentials.function({ bypass: true, userId: "mock_user_123" });
        } else {
            // Real authentication using Telegram initData
            credentials = Realm.Credentials.function({ initData: this.tg.initData });
        }

        this.currentUser = await this.realmApp.logIn(credentials);
        console.log("Authenticated user:", this.currentUser.id);
    }

    async loadData() {
        if (!this.currentUser) return;

        try {
            // Fetch profile
            this.profile = await this.currentUser.functions.getProfile();

            // If running locally and profile is null, mock it
            const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:';
            if (isLocalhost && !this.profile) {
                this.profile = {
                    first_name: "Test",
                    username: "testuser",
                    telegram_id: "mock_user_123",
                    balance: 1500,
                    subscription_end: "2024-12-31 23:59:59",
                    used_configs: [
                        { config_name: "Mock Config", period: "1_month", issue_date: "2023-10-01", config_link: "vless://mock" }
                    ]
                };
            }

            // Fetch available subscription configs
            this.configs = await this.currentUser.functions.getConfigs();

        } catch (error) {
            console.error("Error loading data:", error);
            throw error;
        }
    }

    showLoading(show) {
        const el = document.getElementById('loading');
        if (show) el.classList.remove('hidden');
        else el.classList.add('hidden');
    }

    showError(message) {
        this.tg.showAlert ? this.tg.showAlert(message) : alert(message);
    }

    showView(viewName) {
        const content = document.getElementById('app-content');
        const template = document.getElementById(`tpl-${viewName}`);

        if (!template) return;

        content.innerHTML = '';
        content.appendChild(template.content.cloneNode(true));

        // Render specific view data
        if (viewName === 'profile') this.renderProfile();
        if (viewName === 'buy') this.renderBuy();
        if (viewName === 'configs') this.renderConfigs();
    }

    renderProfile() {
        if (!this.profile) return;

        document.getElementById('p-name').textContent = this.profile.first_name || 'N/A';
        document.getElementById('p-username').textContent = this.profile.username || 'N/A';
        document.getElementById('p-id').textContent = this.profile.telegram_id || 'N/A';
        document.getElementById('p-balance').textContent = this.profile.balance || 0;

        const subStatusEl = document.getElementById('p-sub-status');
        const subEndEl = document.getElementById('p-sub-end');

        if (!this.profile.subscription_end) {
            subStatusEl.textContent = '❌ No Active Subscription';
            subStatusEl.className = 'font-medium text-lg mb-1 text-red-500';
            subEndEl.textContent = '';
        } else {
            const endDate = new Date(this.profile.subscription_end);
            const now = new Date();

            if (endDate > now) {
                const daysLeft = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));
                subStatusEl.textContent = `✅ Active (${daysLeft} days left)`;
                subStatusEl.className = 'font-medium text-lg mb-1 text-green-500';
                subEndEl.textContent = `Until ${endDate.toLocaleDateString()}`;
            } else {
                subStatusEl.textContent = '❌ Expired';
                subStatusEl.className = 'font-medium text-lg mb-1 text-red-500';
                subEndEl.textContent = `Expired on ${endDate.toLocaleDateString()}`;
            }
        }
    }

    renderBuy() {
        if (!this.configs) return;
        const container = document.getElementById('plans-container');
        container.innerHTML = '';

        for (const [key, plan] of Object.entries(this.configs)) {
            const div = document.createElement('div');
            div.className = 'bg-white p-4 rounded-lg shadow border border-gray-100 flex justify-between items-center';
            div.innerHTML = `
                <div>
                    <h3 class="font-bold text-lg">${plan.days} Days</h3>
                    <p class="text-hint">${plan.price} ₽</p>
                </div>
                <button onclick="app.buySubscription('${key}')" class="btn-primary px-4 py-2 rounded-lg font-medium shadow-sm active:scale-95 transition">
                    Buy
                </button>
            `;
            container.appendChild(div);
        }
    }

    renderConfigs() {
        if (!this.profile) return;
        const container = document.getElementById('configs-container');
        container.innerHTML = '';

        const usedConfigs = this.profile.used_configs || [];

        if (usedConfigs.length === 0) {
            container.innerHTML = `<p class="text-hint text-center py-8">No configs yet. Buy a subscription to get one.</p>`;
            return;
        }

        usedConfigs.forEach((conf, idx) => {
            const div = document.createElement('div');
            div.className = 'bg-white p-4 rounded-lg shadow border border-gray-100 break-words';
            div.innerHTML = `
                <h3 class="font-bold mb-1">${conf.config_name}</h3>
                <p class="text-sm text-hint mb-2">Issued: ${conf.issue_date}</p>
                <div class="bg-gray-100 p-2 rounded text-xs font-mono mb-2 overflow-x-auto">
                    ${conf.config_link}
                </div>
                <button onclick="app.copyToClipboard('${conf.config_link}')" class="w-full bg-gray-200 text-gray-800 py-2 rounded font-medium hover:bg-gray-300 transition">
                    Copy Link
                </button>
            `;
            container.appendChild(div);
        });
    }

    async buySubscription(periodKey) {
        this.showLoading(true);
        try {
            const result = await this.currentUser.functions.buySubscription(periodKey);
            if (result.success) {
                this.tg.showAlert ? this.tg.showAlert("Subscription purchased successfully!") : alert("Subscription purchased successfully!");
                await this.loadData();
                this.showView('configs');
            } else {
                this.showError(result.message || "Failed to purchase subscription.");
            }
        } catch (error) {
            console.error("Purchase error:", error);
            this.showError("An error occurred during purchase.");
        } finally {
            this.showLoading(false);
        }
    }

    showTopUpModal() {
        document.getElementById('modal-topup').classList.remove('hidden');
        document.getElementById('modal-topup').classList.add('flex');
    }

    closeModal(id) {
        document.getElementById(id).classList.add('hidden');
        document.getElementById(id).classList.remove('flex');
    }

    setTopUpAmount(amount) {
        document.getElementById('custom-amount').value = amount;
    }

    async processTopUp() {
        const amountInput = document.getElementById('custom-amount').value;
        const amount = parseInt(amountInput);

        if (isNaN(amount) || amount < 50) {
            this.showError("Minimum top up amount is 50 ₽");
            return;
        }

        this.closeModal('modal-topup');
        this.showLoading(true);

        try {
            const result = await this.currentUser.functions.createPayment(amount, "https://t.me/vpni50_bot");
            if (result.success && result.confirmation_url) {
                // Open payment URL
                this.tg.openLink ? this.tg.openLink(result.confirmation_url) : window.open(result.confirmation_url, '_blank');

                // Show instruction to user
                setTimeout(() => {
                    this.tg.showAlert ? this.tg.showAlert("Please complete the payment. Your balance will be updated automatically upon return.") : alert("Please complete the payment.");
                }, 1000);
            } else {
                this.showError(result.message || "Failed to initialize payment.");
            }
        } catch (error) {
            console.error("Payment error:", error);
            this.showError("An error occurred initializing payment.");
        } finally {
            this.showLoading(false);
        }
    }

    copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                this.tg.showPopup ? this.tg.showPopup({ title: 'Success', message: 'Copied to clipboard', buttons: [{type: 'ok'}] }) : alert('Copied to clipboard');
            }).catch(err => {
                console.error('Failed to copy', err);
            });
        } else {
            // Fallback
            const textArea = document.createElement("textarea");
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                this.tg.showPopup ? this.tg.showPopup({ title: 'Success', message: 'Copied to clipboard', buttons: [{type: 'ok'}] }) : alert('Copied to clipboard');
            } catch (err) {
                console.error('Fallback copy failed', err);
            }
            document.body.removeChild(textArea);
        }
    }
}

// Initialize application
const app = new VPNApp();
