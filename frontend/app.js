// Constants
const STITCH_APP_ID = "vpn_bot-xxxxx"; // REPLACE WITH YOUR REALM APP ID

// State
let app;
let user;
let currentUserData = {};
let shopItems = [];

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

// Main Entry Point
async function init() {
    try {
        // Initialize Realm
        app = new Realm.App({ id: STITCH_APP_ID });

        // Authenticate
        const initData = tg.initData;
        if (!initData) {
            console.warn("No initData found. Are you running in Telegram?");
            // For testing locally without Telegram, you might mock this or fail.
        }

        const credentials = Realm.Credentials.function({ initData: initData });
        user = await app.logIn(credentials);

        console.log("Authenticated as:", user.id);

        // Load initial data
        await refreshUserData();
        await loadShop();

        // Hide loading, show app
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('app').classList.remove('hidden');

    } catch (err) {
        console.error("Initialization failed:", err);
        showToast("Failed to connect: " + err.message, true);
    }
}

// Data Fetching
async function refreshUserData() {
    try {
        currentUserData = await user.functions.getUser();
        updateUI(currentUserData);
    } catch (err) {
        console.error("Failed to fetch user data:", err);
        showToast("Error loading profile");
    }
}

async function loadShop() {
    try {
        shopItems = await user.functions.getConfigs(); // This returns the shop list based on backend implementation
        renderShop(shopItems);
    } catch (err) {
        console.error("Failed to fetch shop:", err);
        showToast("Error loading shop");
    }
}

// UI Updates
function updateUI(data) {
    document.getElementById('user-name').textContent = data.first_name || 'User';
    document.getElementById('user-id').textContent = data._id;
    document.getElementById('user-balance').textContent = data.balance.toFixed(2);

    const statusEl = document.getElementById('sub-status');
    const detailsEl = document.getElementById('sub-details');

    if (data.days_left > 0) {
        statusEl.textContent = "Active ✅";
        statusEl.className = "text-lg font-medium text-green-400 mb-1";
        const date = new Date(data.subscription_end).toLocaleDateString();
        detailsEl.textContent = `${data.days_left} days left (until ${date})`;
    } else {
        statusEl.textContent = "Inactive ❌";
        statusEl.className = "text-lg font-medium text-red-400 mb-1";
        detailsEl.textContent = "Buy a subscription to access VPN.";
    }

    // Update Profile / My Configs
    renderMyConfigs(data.used_configs || []);
}

function renderShop(items) {
    const list = document.getElementById('shop-list');
    list.innerHTML = '';

    if (!items || items.length === 0) {
        list.innerHTML = '<p class="text-gray-500">No items available.</p>';
        return;
    }

    items.forEach(item => {
        const div = document.createElement('div');
        div.className = "bg-gray-800 p-4 rounded-xl flex justify-between items-center shadow-md animate-fade-in";
        div.innerHTML = `
            <div>
                <div class="font-bold text-lg">${item.name || item.period}</div>
                <div class="text-sm text-gray-400">${item.days} days</div>
            </div>
            <button onclick="buyItem('${item.id}')" class="bg-blue-600 px-4 py-2 rounded-lg font-bold hover:bg-blue-500 transition">
                ${item.price} ₽
            </button>
        `;
        list.appendChild(div);
    });
}

function renderMyConfigs(configs) {
    const list = document.getElementById('configs-list');
    list.innerHTML = '';

    if (!configs || configs.length === 0) {
        list.innerHTML = '<p class="text-gray-500 text-center py-4">No configs found.</p>';
        return;
    }

    // Show most recent first
    configs.reverse().forEach((conf, idx) => {
        const div = document.createElement('div');
        div.className = "bg-gray-800 p-3 rounded-lg border border-gray-700 space-y-2 animate-fade-in";
        div.innerHTML = `
            <div class="flex justify-between items-center">
                <div class="font-bold text-sm text-gray-300">Config #${configs.length - idx}</div>
                <div class="text-xs text-gray-500">${new Date(conf.assigned_at).toLocaleDateString()}</div>
            </div>
            <div class="bg-gray-900 p-2 rounded text-xs break-all font-mono text-gray-400 select-all cursor-pointer hover:text-white transition" onclick="copyConfig(this.innerText)">
                ${conf.link}
            </div>
            <div class="text-xs text-gray-500 text-right">Click link to copy</div>
        `;
        list.appendChild(div);
    });
}

// Actions
async function buyItem(period) {
    if (!confirm(`Buy subscription for ${period}?`)) return;

    tg.MainButton.showProgress();
    try {
        const result = await user.functions.buySubscription({ period });
        if (result.success) {
            showToast("Success! Subscription active.");
            await refreshUserData();
            switchTab('dashboard'); // Go back to home
        }
    } catch (err) {
        console.error("Purchase failed:", err);
        // Extract error message from Stitch error
        let msg = err.message;
        if (msg.includes("Insufficient balance")) msg = "Insufficient balance!";
        if (msg.includes("No configs available")) msg = "Sold out for this period.";
        showToast(msg, true);
    } finally {
        tg.MainButton.hideProgress();
    }
}

function showTopup() {
    document.getElementById('topup-section').classList.remove('hidden');
    // Scroll to it
    document.getElementById('topup-section').scrollIntoView({ behavior: 'smooth' });
}

function setTopupAmount(amt) {
    document.getElementById('custom-amount').value = amt;
}

async function initiatePayment() {
    const amtInput = document.getElementById('custom-amount');
    const amount = parseFloat(amtInput.value);

    if (!amount || amount < 50) {
        showToast("Minimum amount is 50₽", true);
        return;
    }

    tg.MainButton.showProgress();
    try {
        const result = await user.functions.createPayment({ amount });
        if (result.confirmation_url) {
            tg.openLink(result.confirmation_url);
            showToast("Payment link opened. Check status later.");
            // Ideally start polling or ask user to refresh manually
            setTimeout(refreshUserData, 10000); // Check after 10s
        }
    } catch (err) {
        console.error("Payment failed:", err);
        showToast("Payment creation failed: " + err.message, true);
    } finally {
        tg.MainButton.hideProgress();
    }
}

function copyConfig(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast("Copied to clipboard!");
    }).catch(() => {
        showToast("Failed to copy", true);
    });
}

function switchTab(tabName) {
    // Hide all views
    document.querySelectorAll('[id^="view-"]').forEach(el => el.classList.add('hidden'));
    // Show selected
    document.getElementById(`view-${tabName}`).classList.remove('hidden');

    // Update buttons
    const tabs = ['dashboard', 'shop', 'profile'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab-${t}`);
        if (t === tabName) {
            btn.classList.add('bg-blue-600', 'text-white');
            btn.classList.remove('text-gray-400');
        } else {
            btn.classList.remove('bg-blue-600', 'text-white');
            btn.classList.add('text-gray-400');
        }
    });
}

function showToast(msg, isError = false) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `fixed bottom-4 left-1/2 transform -translate-x-1/2 px-4 py-2 rounded-lg shadow-xl border transition-opacity z-50 ${isError ? 'bg-red-800 border-red-600 text-white' : 'bg-gray-800 border-gray-600 text-white'}`;
    t.style.opacity = '1';
    setTimeout(() => { t.style.opacity = '0'; }, 3000);
}

// Start
window.addEventListener('load', init);
