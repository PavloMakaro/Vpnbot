// Initialize Realm App
const APP_ID = "vpn-bot-app-id"; // REPLACE WITH YOUR REALM APP ID
const app = new Realm.App({ id: APP_ID });

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// State
let currentUser = null;
let userProfile = null;

// DOM Elements
const views = {
    home: document.getElementById('view-home'),
    shop: document.getElementById('view-shop'),
    topup: document.getElementById('view-topup'),
    configs: document.getElementById('view-configs'),
    support: document.getElementById('view-support')
};

const loadingOverlay = document.getElementById('loading');
const balanceDisplay = document.getElementById('user-balance');
const subscriptionStatus = document.getElementById('subscription-status');

// Router
const router = {
    navigate: (viewName) => {
        Object.values(views).forEach(el => el.classList.add('hidden'));
        if (views[viewName]) {
            views[viewName].classList.remove('hidden');
        }

        // Refresh data if needed
        if (viewName === 'home') loadProfile();
        if (viewName === 'configs') loadConfigs();

        tg.MainButton.hide();
        if (viewName === 'topup') {
            tg.MainButton.setText("PAY");
            tg.MainButton.show();
            tg.MainButton.onClick(initiatePayment);
        } else {
            tg.MainButton.offClick(initiatePayment);
        }
    }
};

// Auth
async function login() {
    try {
        const credentials = Realm.Credentials.function({
            initData: tg.initData
        });
        currentUser = await app.logIn(credentials);
        console.log("Logged in:", currentUser.id);
        await loadProfile();
    } catch (err) {
        console.error("Login failed:", err);
        alert("Authentication failed. Please open from Telegram.");
    }
}

// Data Fetching
async function loadProfile() {
    if (!currentUser) return;
    try {
        loadingOverlay.classList.remove('hidden');
        userProfile = await currentUser.functions.getUserProfile();

        // Update UI
        balanceDisplay.textContent = `${userProfile.balance || 0} ₽`;

        if (userProfile.subscription_end && new Date(userProfile.subscription_end) > new Date()) {
            const endDate = new Date(userProfile.subscription_end).toLocaleDateString();
            subscriptionStatus.innerHTML = `<span class="text-green-600 font-bold">Active until ${endDate}</span>`;
        } else {
            subscriptionStatus.innerHTML = `<span class="text-red-500 font-bold">Inactive</span>`;
        }
    } catch (err) {
        console.error("Failed to load profile:", err);
    } finally {
        loadingOverlay.classList.add('hidden');
    }
}

async function loadConfigs() {
    if (!currentUser) return;
    const listEl = document.getElementById('configs-list');
    listEl.innerHTML = '<div class="text-center py-4">Loading...</div>';

    try {
        const configs = await currentUser.functions.getConfigs();

        if (configs.length === 0) {
            listEl.innerHTML = '<div class="text-center py-4 text-gray-500">No configs found. Buy a subscription first.</div>';
            return;
        }

        listEl.innerHTML = configs.map(config => `
            <div class="bg-gray-50 p-3 rounded border border-gray-200">
                <div class="font-bold">${config.name}</div>
                <div class="text-xs text-gray-500 mb-2">${config.period}</div>
                <div class="bg-gray-200 p-2 rounded text-xs break-all select-all cursor-pointer font-mono" onclick="copyToClipboard('${config.link}')">
                    ${config.link.substring(0, 30)}...
                </div>
                <button onclick="copyToClipboard('${config.link}')" class="mt-2 text-blue-600 text-sm hover:underline">Copy Link</button>
            </div>
        `).join('');
    } catch (err) {
        listEl.innerHTML = `<div class="text-red-500">Error loading configs: ${err.message}</div>`;
    }
}

// Actions
async function purchase(period) {
    if (!confirm(`Are you sure you want to buy ${period} subscription?`)) return;

    try {
        loadingOverlay.classList.remove('hidden');
        const result = await currentUser.functions.buySubscription(period);
        alert("Success! Config assigned.");
        router.navigate('configs');
    } catch (err) {
        alert("Purchase failed: " + err.message);
    } finally {
        loadingOverlay.classList.add('hidden');
        loadProfile();
    }
}

async function initiatePayment() {
    const amountInput = document.getElementById('topup-amount');
    const amount = parseFloat(amountInput.value);

    if (!amount || amount < 50) {
        alert("Minimum amount is 50 ₽");
        return;
    }

    try {
        loadingOverlay.classList.remove('hidden');
        const result = await currentUser.functions.createPayment(amount);

        if (result && result.confirmation_url) {
             tg.openLink(result.confirmation_url);
        } else {
            alert("Failed to create payment link");
        }
    } catch (err) {
        alert("Payment error: " + err.message);
    } finally {
        loadingOverlay.classList.add('hidden');
    }
}

function setAmount(val) {
    document.getElementById('topup-amount').value = val;
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        tg.showPopup({ message: 'Copied to clipboard!' });
    });
}

// Start
document.addEventListener('DOMContentLoaded', () => {
    // Check if running in Telegram
    if (!tg.initDataUnsafe || !tg.initDataUnsafe.user) {
        // Mock login for development if needed, or show error
        // console.warn("Not running in Telegram");
    }

    login();

    // Setup initial view
    router.navigate('home');

    // Setup bottom nav listeners
    document.querySelectorAll('nav button').forEach(btn => {
        // simple way to bind specific nav items
        // logic handled in HTML onclick for simplicity
    });
});
