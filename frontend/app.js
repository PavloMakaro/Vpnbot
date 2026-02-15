const tg = window.Telegram.WebApp;
tg.expand();

// CONFIGURATION - REPLACE WITH YOUR ATLAS APP ID
const APP_ID = "vpn_bot-xxxxx";

const app = new Realm.App({ id: APP_ID });
let user = null; // Atlas User
let dbUser = null; // MongoDB User Document

// UI Elements
const els = {
    username: document.getElementById('username'),
    userId: document.getElementById('user-id'),
    avatar: document.getElementById('user-avatar'),
    balance: document.getElementById('balance'),
    statusBanner: document.getElementById('status-banner'),
    daysLeft: document.getElementById('days-left'),
    plansContainer: document.getElementById('plans-container'),
    configsContainer: document.getElementById('configs-container'),
    customAmount: document.getElementById('custom-amount'),
    notif: document.getElementById('notification'),
    notifMsg: document.getElementById('notif-message')
};

// Tabs
function switchTab(tab) {
    document.querySelectorAll('section').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('nav button').forEach(el => {
        el.classList.remove('bg-blue-600', 'text-white');
        el.classList.add('text-gray-400');
    });

    document.getElementById(`${tab}-section`).classList.remove('hidden');
    const btn = document.getElementById(`tab-${tab}`);
    btn.classList.remove('text-gray-400');
    btn.classList.add('bg-blue-600', 'text-white');
}

// Notifications
function showNotification(msg, isError = false) {
    els.notifMsg.textContent = msg;
    els.notif.classList.remove('hidden');
    els.notif.classList.add(isError ? 'border-red-500' : 'border-green-500');
    setTimeout(() => els.notif.classList.add('hidden'), 3000);
}

// Auth & Init
async function init() {
    try {
        // Authenticate with Atlas using Telegram initData
        // This assumes you configured "Custom Function Authentication" in Atlas
        // and linked it to the 'auth' function.
        const credentials = Realm.Credentials.function({ initData: tg.initData });
        user = await app.logIn(credentials);

        // Fetch initial data
        await refreshData();

        // Render Plans
        await renderPlans();

        // Setup Main Button
        tg.MainButton.setText("CLOSE");
        tg.MainButton.onClick(() => tg.close());
        tg.MainButton.show();

    } catch (err) {
        console.error("Auth Error:", err);
        showNotification("Authentication failed. " + err.message, true);
    }
}

async function refreshData() {
    try {
        dbUser = await user.functions.getUserProfile();
        renderProfile(dbUser);
        if (dbUser.subscription_active) {
            await renderConfigs();
        }
    } catch (err) {
        console.error("Refresh Error:", err);
    }
}

function renderProfile(u) {
    els.username.textContent = u.username || "User";
    els.userId.textContent = u._id;
    els.balance.textContent = `${u.balance} ₽`;

    if (u.subscription_active) {
        els.statusBanner.classList.remove('bg-red-900/50', 'border-red-700');
        els.statusBanner.classList.add('bg-green-900/50', 'border-green-700');
        els.statusBanner.innerHTML = `
            <p class="text-sm font-medium text-green-200">Subscription Active</p>
            <p class="text-xs text-green-300 mt-1">${u.days_left} days left</p>
        `;
    } else {
        els.statusBanner.classList.add('bg-red-900/50', 'border-red-700');
        els.statusBanner.classList.remove('bg-green-900/50', 'border-green-700');
        els.statusBanner.innerHTML = `
            <p class="text-sm font-medium text-red-200">Subscription Inactive</p>
            <p class="text-xs text-red-300 mt-1">Tap 'Shop' to buy</p>
        `;
    }
}

async function renderPlans() {
    try {
        const plans = await user.functions.getPlans();
        els.plansContainer.innerHTML = '';

        Object.entries(plans).forEach(([key, plan]) => {
            const div = document.createElement('div');
            div.className = "p-4 bg-gray-800 rounded-lg border border-gray-700 flex justify-between items-center";
            div.innerHTML = `
                <div>
                    <p class="font-bold text-lg">${plan.days} Days</p>
                    <p class="text-sm text-gray-400">Standard VPN</p>
                </div>
                <div class="text-right">
                    <p class="font-bold text-xl mb-1">${plan.price} ₽</p>
                    <button onclick="buySubscription('${key}')" class="px-4 py-2 bg-blue-600 rounded text-sm font-bold hover:bg-blue-700">Buy</button>
                </div>
            `;
            els.plansContainer.appendChild(div);
        });
    } catch (err) {
        els.plansContainer.innerHTML = `<p class="text-red-400">Failed to load plans</p>`;
    }
}

async function renderConfigs() {
    try {
        const configs = await user.functions.getMyConfigs();
        const container = els.configsContainer;
        container.innerHTML = '';

        if (configs.length === 0) {
            container.innerHTML = `<p class="text-center text-gray-500 py-8">No configurations found.</p>`;
            return;
        }

        configs.forEach((conf, idx) => {
            const div = document.createElement('div');
            div.className = "p-4 bg-gray-800 rounded-lg border border-gray-700";
            div.innerHTML = `
                <div class="flex justify-between mb-2">
                    <span class="font-bold text-purple-300">${conf.name}</span>
                    <span class="text-xs text-gray-500">${new Date(conf.used_at).toLocaleDateString()}</span>
                </div>
                <div class="bg-gray-900 p-2 rounded text-xs break-all font-mono text-gray-400 mb-2 h-16 overflow-y-auto">
                    ${conf.link}
                </div>
                <button onclick="copyToClipboard('${conf.link}')" class="w-full py-2 bg-purple-600/20 text-purple-300 rounded hover:bg-purple-600/30 transition">Copy Link</button>
            `;
            container.appendChild(div);
        });
    } catch (err) {
        console.error(err);
    }
}

// Actions
async function buySubscription(periodKey) {
    if (!confirm("Confirm purchase?")) return;

    tg.MainButton.showProgress();
    try {
        const result = await user.functions.buySubscription(periodKey);
        if (result.success) {
            showNotification("Purchase successful!");
            await refreshData();
            switchTab('configs');
        }
    } catch (err) {
        showNotification(err.message || "Purchase failed", true);
    }
    tg.MainButton.hideProgress();
}

function selectAmount(amt) {
    els.customAmount.value = amt;
}

async function initiatePayment() {
    const amt = parseFloat(els.customAmount.value);
    if (!amt || amt < 10) {
        showNotification("Minimum amount is 10 RUB", true);
        return;
    }

    tg.MainButton.showProgress();
    try {
        const res = await user.functions.createPayment(amt);
        if (res.payment_url) {
            tg.openLink(res.payment_url);
            // Poll for payment completion
            pollPayment(res.payment_id);
        }
    } catch (err) {
        showNotification("Payment Error: " + err.message, true);
    }
    tg.MainButton.hideProgress();
}

async function pollPayment(paymentId) {
    let attempts = 0;
    const maxAttempts = 20; // 1 minute approx

    const interval = setInterval(async () => {
        attempts++;
        if (attempts > maxAttempts) {
            clearInterval(interval);
            return;
        }

        try {
            const res = await user.functions.checkPayment(paymentId);
            if (res.status === 'succeeded') {
                clearInterval(interval);
                showNotification("Payment Successful!");
                await refreshData();
            }
        } catch (e) {
            console.error(e);
        }
    }, 3000);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification("Copied to clipboard!");
    });
}

// Start
init();
