// Configuration
const REALM_APP_ID = "vpn_bot-tma"; // Replace with your actual App ID
let app;
let currentUser;
let telegram;
let tgUser;

// State
let state = {
    profile: null,
    configs: null,
    currentPaymentId: null,
    paymentInterval: null,
    view: 'dashboard'
};

// UI Elements
const els = {
    mainLoader: document.getElementById('main-loader'),
    errorMessage: document.getElementById('error-message'),
    errorText: document.getElementById('error-text'),
    mainContent: document.getElementById('main-content'),
    viewDashboard: document.getElementById('view-dashboard'),
    viewStore: document.getElementById('view-store'),
    viewTopup: document.getElementById('view-topup'),
    userGreeting: document.getElementById('user-greeting'),
    userBalance: document.getElementById('user-balance'),
    subStatusActive: document.getElementById('sub-status-active'),
    subStatusInactive: document.getElementById('sub-status-inactive'),
    subEndDate: document.getElementById('sub-end-date'),
    subDaysLeft: document.getElementById('sub-days-left'),
    configsList: document.getElementById('configs-list'),
    noConfigsMsg: document.getElementById('no-configs-msg'),
    storePlans: document.getElementById('store-plans'),
    customAmount: document.getElementById('custom-amount'),
    paymentStatus: document.getElementById('payment-status')
};

// Initialization
async function init() {
    try {
        telegram = window.Telegram.WebApp;
        telegram.expand();
        telegram.ready();

        const initData = telegram.initData || '';
        if (!initData && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
            throw new Error("Telegram InitData is missing. Open this app inside Telegram.");
        }

        tgUser = telegram.initDataUnsafe?.user || { first_name: "Guest", id: "123" };

        els.userGreeting.textContent = `Hello, ${tgUser.first_name}!`;

        app = new Realm.App({ id: REALM_APP_ID });

        // Mocking for local dev/testing
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:') {
            console.warn("Local development mode: Mocking authentication.");
            // Proceed to mock loading
            setTimeout(mockLoadProfile, 1000);
            return;
        }

        // Authenticate via Custom Function using Telegram initData
        const credentials = Realm.Credentials.function({ initData });
        currentUser = await app.logIn(credentials);

        await loadData();

    } catch (error) {
        console.error("Init Error:", error);
        showError(error.message);
    }
}

async function loadData() {
    showLoader();
    try {
        // Fetch profile
        state.profile = await currentUser.functions.getProfile();
        // Fetch configs pricing
        state.configs = await currentUser.functions.getConfigs();

        renderProfile();
        renderStore();
        showDashboard();
    } catch (error) {
        console.error("Load Data Error:", error);
        showError("Failed to load data. Please try again.");
    }
    hideLoader();
}

// Rendering
function renderProfile() {
    const { profile } = state;

    // Balance
    els.userBalance.textContent = profile.balance.toString();

    // Subscription
    if (profile.days_left > 0) {
        els.subStatusActive.classList.remove('hidden');
        els.subStatusInactive.classList.add('hidden');
        els.subEndDate.textContent = profile.subscription_end.split(',')[0];
        els.subDaysLeft.textContent = profile.days_left;
    } else {
        els.subStatusActive.classList.add('hidden');
        els.subStatusInactive.classList.remove('hidden');
    }

    // Configs
    els.configsList.innerHTML = '';
    const usedConfigs = profile.used_configs || [];

    if (usedConfigs.length === 0) {
        els.noConfigsMsg.classList.remove('hidden');
    } else {
        els.noConfigsMsg.classList.add('hidden');
        usedConfigs.forEach((cfg, idx) => {
            const configDiv = document.createElement('div');
            configDiv.className = 'p-3 bg-gray-50 border border-gray-200 rounded-lg slide-up text-sm';
            configDiv.style.animationDelay = `${idx * 0.1}s`;

            const linkDisplay = cfg.config_link.length > 30 ? cfg.config_link.substring(0, 30) + '...' : cfg.config_link;

            configDiv.innerHTML = `
                <div class="flex justify-between items-center mb-1">
                    <span class="font-bold text-gray-800">${cfg.config_name}</span>
                    <span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">${cfg.period.replace('_', ' ')}</span>
                </div>
                <div class="flex flex-col mt-2">
                    <code class="bg-gray-200 p-2 rounded text-xs overflow-hidden text-ellipsis mb-2">${linkDisplay}</code>
                    <button onclick="copyToClipboard('${cfg.config_link}', this)" class="bg-blue-500 hover:bg-blue-600 text-white py-1 px-3 rounded text-xs transition self-end">Copy Link</button>
                </div>
            `;
            els.configsList.appendChild(configDiv);
        });
    }
}

function renderStore() {
    els.storePlans.innerHTML = '';
    const { configs, profile } = state;

    if (!configs) return;

    Object.entries(configs).forEach(([periodKey, data], idx) => {
        const canAfford = profile.balance >= data.price;
        const planDiv = document.createElement('div');
        planDiv.className = 'card slide-up p-4 border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer';
        planDiv.style.animationDelay = `${idx * 0.1}s`;
        planDiv.onclick = () => canAfford ? confirmPurchase(periodKey, data) : showTopUp();

        planDiv.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <h3 class="font-bold text-gray-800 text-lg">${data.days} Days VPN</h3>
                    <p class="text-sm opacity-70">${data.price} ₽</p>
                </div>
                <div class="${canAfford ? 'text-blue-500' : 'text-red-400'}">
                    ${canAfford ? 'Buy' : 'Top up'} →
                </div>
            </div>
        `;
        els.storePlans.appendChild(planDiv);
    });
}

// Actions
async function confirmPurchase(periodKey, data) {
    if (confirm(`Buy ${data.days} days subscription for ${data.price} ₽?`)) {
        showLoader();
        try {
            const result = await currentUser.functions.buySubscription(periodKey);
            if (result.success) {
                telegram.showAlert(result.message);
                await loadData();
            }
        } catch (error) {
            console.error("Purchase Error:", error);
            telegram.showAlert(error.message || "Failed to purchase.");
        }
        hideLoader();
    }
}

function setTopUpAmount(amount) {
    els.customAmount.value = amount;
}

async function processTopUp() {
    const amount = parseInt(els.customAmount.value);
    if (isNaN(amount) || amount < 50 || amount > 50000) {
        telegram.showAlert("Please enter a valid amount between 50 and 50,000.");
        return;
    }

    showLoader();
    try {
        const result = await currentUser.functions.createPayment(amount, window.location.href);
        state.currentPaymentId = result.payment_id;

        // Open payment URL
        telegram.openLink(result.confirmation_url);

        // Show status checker
        els.paymentStatus.classList.remove('hidden');

        // Start polling
        state.paymentInterval = setInterval(checkCurrentPayment, 10000);

    } catch (error) {
        console.error("Payment Error:", error);
        telegram.showAlert(error.message || "Failed to create payment.");
    }
    hideLoader();
}

async function checkCurrentPayment() {
    if (!state.currentPaymentId) return;

    try {
        const result = await currentUser.functions.checkPayment(state.currentPaymentId);
        if (result.status === 'confirmed') {
            clearInterval(state.paymentInterval);
            els.paymentStatus.classList.add('hidden');
            state.currentPaymentId = null;
            telegram.showAlert(`Success! Added ${result.amount} ₽ to your balance.`);
            await loadData();
            showDashboard();
        } else if (result.status === 'canceled') {
            cancelPaymentWait();
            telegram.showAlert("Payment was canceled.");
        }
    } catch (error) {
        console.error("Check Payment Error:", error);
    }
}

function cancelPaymentWait() {
    if (state.paymentInterval) clearInterval(state.paymentInterval);
    state.currentPaymentId = null;
    els.paymentStatus.classList.add('hidden');
}

// Utils
function copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
        const oldText = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('bg-green-500');
        btn.classList.remove('bg-blue-500');
        setTimeout(() => {
            btn.textContent = oldText;
            btn.classList.remove('bg-green-500');
            btn.classList.add('bg-blue-500');
        }, 2000);
    });
}

// Navigation View switching
function showDashboard() {
    state.view = 'dashboard';
    els.viewStore.classList.add('hidden');
    els.viewTopup.classList.add('hidden');
    els.viewDashboard.classList.remove('hidden');
}

function showStore() {
    state.view = 'store';
    els.viewDashboard.classList.add('hidden');
    els.viewTopup.classList.add('hidden');
    els.viewStore.classList.remove('hidden');
}

function showTopUp() {
    state.view = 'topup';
    els.viewDashboard.classList.add('hidden');
    els.viewStore.classList.add('hidden');
    els.viewTopup.classList.remove('hidden');
}

// Loading/Error states
function showLoader() {
    els.mainLoader.classList.remove('hidden');
    els.mainContent.classList.add('hidden');
    els.errorMessage.classList.add('hidden');
}

function hideLoader() {
    els.mainLoader.classList.add('hidden');
    els.mainContent.classList.remove('hidden');
}

function showError(msg) {
    els.mainLoader.classList.add('hidden');
    els.mainContent.classList.add('hidden');
    els.errorMessage.classList.remove('hidden');
    els.errorText.textContent = msg;
}

// Start app
window.addEventListener('DOMContentLoaded', init);

// -- Mock data for local testing --
function mockLoadProfile() {
    state.profile = {
        balance: 150,
        days_left: 12,
        subscription_end: new Date(Date.now() + 12*24*60*60*1000).toLocaleString(),
        used_configs: [
            {
                config_name: "Config_1_month_1",
                config_link: "vless://mock-link-1234567890@test.com:443?type=tcp",
                period: "1_month"
            }
        ]
    };
    state.configs = {
        '1_month': { price: 50, days: 30 },
        '2_months': { price: 90, days: 60 },
        '3_months': { price: 120, days: 90 }
    };

    // override functions
    currentUser = {
        functions: {
            getProfile: async () => state.profile,
            getConfigs: async () => state.configs,
            buySubscription: async (p) => {
                state.profile.balance -= state.configs[p].price;
                return { success: true, message: "Mock purchased!" };
            },
            createPayment: async (a, r) => { return { payment_id: 'mock_id', confirmation_url: 'https://example.com' }; },
            checkPayment: async (id) => { return { status: 'confirmed', amount: parseInt(els.customAmount.value) }; }
        }
    };

    // override telegram UI functions
    telegram.showAlert = (msg) => alert(msg);
    telegram.openLink = (url) => window.open(url, '_blank');

    renderProfile();
    renderStore();
    showDashboard();
    hideLoader();
}