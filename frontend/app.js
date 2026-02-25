// MongoDB Atlas App Services App ID - REPLACE THIS!
const APP_ID = "vpn-bot-xxxxx";

const app = new Realm.App({ id: APP_ID });
const tg = window.Telegram.WebApp;

// Expand to full height
tg.expand();

// DOM Elements
const views = {
    home: document.getElementById('view-home'),
    buy: document.getElementById('view-buy'),
    topup: document.getElementById('view-topup'),
    payment: document.getElementById('view-payment')
};

const els = {
    loading: document.getElementById('loading'),
    error: document.getElementById('error'),
    errorMsg: document.getElementById('error-msg'),
    userName: document.getElementById('user-name'),
    userBalance: document.getElementById('user-balance'),
    subStatus: document.getElementById('subscription-status'),
    subText: document.getElementById('sub-text'),
    configsList: document.getElementById('configs-list'),
    plansList: document.getElementById('plans-list'),
    topupAmount: document.getElementById('topup-amount'),
    paymentStatus: document.getElementById('payment-status')
};

let currentUser = null;
let currentPaymentId = null;

async function init() {
    try {
        if (!tg.initData) {
            throw new Error("Please open this app from Telegram.");
        }

        // Authenticate
        // We pass the raw initData string to the custom auth function
        const credentials = Realm.Credentials.custom(tg.initData);
        currentUser = await app.logIn(credentials);

        console.log("Logged in as:", currentUser.id);

        await loadProfile();
        setupNavigation();

        showView('home');
    } catch (err) {
        console.error("Init error:", err);
        showError(err.message || "Failed to initialize app");
    } finally {
        els.loading.classList.add('hidden');
    }
}

async function loadProfile() {
    try {
        const profile = await currentUser.functions.getProfile();

        els.userName.innerText = `${profile.first_name} (@${profile.username})`;
        els.userBalance.innerText = profile.balance || 0;

        if (profile.daysLeft > 0) {
            els.subText.innerText = `Active: ${profile.daysLeft} days left`;
            els.subStatus.className = "mb-4 p-3 bg-green-50 rounded text-sm text-green-800 flex items-center gap-2";
        } else {
            els.subText.innerText = "No active subscription";
            els.subStatus.className = "mb-4 p-3 bg-red-50 rounded text-sm text-red-800 flex items-center gap-2";
        }

        renderConfigs(profile.used_configs || []);

    } catch (err) {
        console.error("Load profile error:", err);
        showError("Failed to load profile");
    }
}

function renderConfigs(configs) {
    els.configsList.innerHTML = '';
    if (configs.length === 0) {
        els.configsList.innerHTML = '<p class="text-gray-500 text-sm italic text-center py-4">You have no active configurations.</p>';
        return;
    }

    // Sort by issue date descending
    configs.sort((a, b) => new Date(b.issue_date) - new Date(a.issue_date));

    configs.forEach(config => {
        const div = document.createElement('div');
        div.className = "border rounded p-3 bg-gray-50";
        div.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <span class="font-bold text-sm">${config.config_name}</span>
                <span class="text-xs text-gray-500">${new Date(config.issue_date).toLocaleDateString()}</span>
            </div>
            <div class="text-xs bg-gray-200 p-2 rounded break-all font-mono select-all cursor-pointer hover:bg-gray-300 transition" onclick="copyToClipboard('${config.config_link}')">
                ${config.config_link.substring(0, 30)}...
            </div>
            <p class="text-xs text-gray-400 mt-1 text-center">Click link to copy</p>
        `;
        els.configsList.appendChild(div);
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        tg.showPopup({ message: "Link copied to clipboard!" });
    });
}

async function loadPlans() {
    try {
        const plans = await currentUser.functions.getConfigs();
        els.plansList.innerHTML = '';

        Object.entries(plans).forEach(([key, plan]) => {
            const div = document.createElement('div');
            div.className = "bg-white p-4 rounded-lg shadow border flex justify-between items-center";

            const btnClass = plan.available
                ? "bg-blue-500 hover:bg-blue-600 text-white"
                : "bg-gray-300 text-gray-500 cursor-not-allowed";

            div.innerHTML = `
                <div>
                    <h3 class="font-bold">${plan.name || key}</h3>
                    <p class="text-sm text-gray-600">${plan.days} days</p>
                </div>
                <div class="text-right">
                    <p class="font-bold text-lg mb-1">${plan.price} ₽</p>
                    <button class="px-4 py-2 rounded text-sm ${btnClass} transition"
                        onclick="buySubscription('${key}')"
                        ${!plan.available ? 'disabled' : ''}>
                        ${plan.available ? 'Buy' : 'Sold Out'}
                    </button>
                </div>
            `;
            els.plansList.appendChild(div);
        });
    } catch (err) {
        console.error("Load plans error:", err);
        tg.showAlert("Failed to load plans");
    }
}

async function buySubscription(period) {
    tg.MainButton.showProgress();
    try {
        const result = await currentUser.functions.buySubscription(period);
        tg.MainButton.hideProgress();

        if (result.success) {
            tg.showPopup({
                title: "Success!",
                message: "Subscription purchased successfully.",
                buttons: [{ type: "ok" }]
            });
            await loadProfile();
            showView('home');
        } else {
             tg.showAlert(result.message || "Purchase failed");
        }
    } catch (err) {
        tg.MainButton.hideProgress();
        console.error("Buy error:", err);
        tg.showAlert(err.message || "Purchase failed");
    }
}

async function createPayment() {
    const amount = parseFloat(els.topupAmount.value);
    if (isNaN(amount) || amount < 50) {
        tg.showAlert("Minimum amount is 50 ₽");
        return;
    }

    tg.MainButton.showProgress();
    try {
        const result = await currentUser.functions.createPayment(amount);
        tg.MainButton.hideProgress();

        currentPaymentId = result.payment_id;

        // Open payment link
        tg.openLink(result.confirmation_url);

        // Show payment status view
        showView('payment');
        checkPaymentStatus();

    } catch (err) {
        tg.MainButton.hideProgress();
        console.error("Payment error:", err);
        tg.showAlert(err.message || "Failed to create payment");
    }
}

async function checkPaymentStatus() {
    if (!currentPaymentId) return;

    els.paymentStatus.innerText = "Checking...";
    try {
        const result = await currentUser.functions.checkPayment(currentPaymentId);
        els.paymentStatus.innerText = result.status.toUpperCase();

        if (result.status === 'succeeded') {
            tg.showPopup({ title: "Success", message: "Payment successful!" });
            currentPaymentId = null;
            await loadProfile();
            showView('home');
        } else if (result.status === 'canceled') {
            els.paymentStatus.className = "text-lg font-bold text-red-600 mb-6 bg-red-50 py-2 rounded";
        } else {
             els.paymentStatus.className = "text-lg font-bold text-yellow-600 mb-6 bg-yellow-50 py-2 rounded";
        }
    } catch (err) {
        console.error("Check payment error:", err);
        els.paymentStatus.innerText = "Error checking status";
    }
}

// Navigation
function showView(viewId) {
    Object.values(views).forEach(el => el.classList.add('hidden'));
    views[viewId].classList.remove('hidden');

    // Back button handling
    if (viewId === 'home') {
        tg.BackButton.hide();
    } else {
        tg.BackButton.show();
        tg.BackButton.onClick(() => showView('home'));
    }
}

function showError(msg) {
    els.loading.classList.add('hidden');
    els.error.classList.remove('hidden');
    els.errorMsg.innerText = msg;
}

function setupNavigation() {
    document.querySelectorAll('.back-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.target;
            showView(target);
        });
    });

    document.getElementById('btn-buy').addEventListener('click', () => {
        showView('buy');
        loadPlans();
    });

    document.getElementById('btn-topup').addEventListener('click', () => {
        showView('topup');
    });

    // Amount presets
    document.querySelectorAll('.amount-preset').forEach(btn => {
        btn.addEventListener('click', () => {
            els.topupAmount.value = btn.dataset.amount;
        });
    });

    document.getElementById('btn-pay').addEventListener('click', createPayment);
    document.getElementById('btn-check-payment').addEventListener('click', checkPaymentStatus);
}

// Expose functions to global scope for onclick handlers
window.buySubscription = buySubscription;

// Start
init();
