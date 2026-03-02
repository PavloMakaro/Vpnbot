// Replace with your MongoDB Realm App ID
const REALM_APP_ID = "vpn_bot-xxxxx"; // User must replace this
const app = new Realm.App({ id: REALM_APP_ID });

let tg = window.Telegram.WebApp;
tg.expand();

// Initialize UI
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await initApp();
    } catch (error) {
        showError("Initialization failed: " + error.message);
    }
});

async function initApp() {
    // 1. Authenticate with Realm using Telegram initData
    const initData = tg.initData || "dummy_init_data_for_testing";

    // For custom function auth:
    const credentials = Realm.Credentials.function(initData);

    try {
        await app.logIn(credentials);

        // 2. Load Dashboard Data
        await loadProfile();

        // 3. Load Products (Configs) for Buy View
        await loadProducts();

        // 4. Hide loading, show app
        document.getElementById('loading').style.display = 'none';
        document.getElementById('app-content').classList.remove('hidden');

    } catch (err) {
        console.error("Login Error:", err);
        showError("Failed to login. Please try again later.");
    }
}

async function loadProfile() {
    try {
        const profile = await app.currentUser.functions.getProfile();

        // Update Header
        document.getElementById('display-name').innerText = profile.first_name || 'User';
        document.getElementById('display-username').innerText = profile.username ? `@${profile.username}` : '';
        document.getElementById('display-balance').innerText = `${profile.balance} ₽`;

        // Update Subscription Status
        const statusIcon = document.getElementById('sub-status-icon');
        const statusText = document.getElementById('sub-status-text');
        const statusDetail = document.getElementById('sub-status-detail');

        if (profile.days_left > 0) {
            statusIcon.className = "h-10 w-10 rounded-full flex items-center justify-center mr-3 bg-green-900 text-green-400";
            statusIcon.innerHTML = `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
            statusText.innerText = "Active";
            statusText.className = "text-xl font-bold text-green-400";
            statusDetail.innerText = `${profile.days_left} days remaining`;
        } else {
            statusIcon.className = "h-10 w-10 rounded-full flex items-center justify-center mr-3 bg-red-900 text-red-400";
            statusIcon.innerHTML = `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>`;
            statusText.innerText = "Inactive";
            statusText.className = "text-xl font-bold text-red-400";
            statusDetail.innerText = "No active subscription";
        }

        // Update Configs List
        const configsContainer = document.getElementById('configs-container');
        configsContainer.innerHTML = '';

        if (profile.used_configs && profile.used_configs.length > 0) {
            profile.used_configs.reverse().forEach(config => {
                const configEl = document.createElement('div');
                configEl.className = "bg-gray-800 p-4 rounded-xl shadow border border-gray-700";
                configEl.innerHTML = `
                    <div class="flex justify-between items-center mb-2">
                        <h3 class="font-bold text-gray-200 text-sm truncate pr-2">${config.config_name}</h3>
                        <span class="text-xs text-gray-400 whitespace-nowrap">${new Date(config.issue_date).toLocaleDateString()}</span>
                    </div>
                    <div class="flex">
                        <input type="text" readonly class="bg-gray-900 border border-gray-600 text-xs rounded block w-full p-2 mr-2 text-gray-400" value="${config.config_link}">
                        <button onclick="copyToClipboardText('${config.config_link}')" class="bg-gray-700 hover:bg-gray-600 text-white p-2 rounded transition">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
                        </button>
                    </div>
                `;
                configsContainer.appendChild(configEl);
            });
        } else {
            configsContainer.innerHTML = `<p class="text-gray-500 text-sm text-center py-4">You have no configs yet.</p>`;
        }

    } catch (err) {
        console.error("Load Profile Error:", err);
    }
}

async function loadProducts() {
    try {
        const products = await app.currentUser.functions.getConfigs();
        const container = document.getElementById('products-container');
        container.innerHTML = '';

        for (const [key, data] of Object.entries(products)) {
            const isAvailable = data.available_configs > 0;
            const btnClass = isAvailable ? "bg-blue-600 hover:bg-blue-500" : "bg-gray-700 cursor-not-allowed opacity-50";
            const btnAction = isAvailable ? `onclick="buySubscription('${key}', ${data.price})"` : "";
            const availText = isAvailable ? "Available" : "Out of stock";

            const productEl = document.createElement('div');
            productEl.className = "bg-gray-800 rounded-xl p-4 border border-gray-700 flex justify-between items-center shadow";
            productEl.innerHTML = `
                <div>
                    <h3 class="text-lg font-bold">${data.days} Days</h3>
                    <p class="text-sm text-gray-400">${availText}</p>
                </div>
                <button ${btnAction} class="${btnClass} font-bold py-2 px-6 rounded-lg transition shadow">
                    ${data.price} ₽
                </button>
            `;
            container.appendChild(productEl);
        }
    } catch (err) {
        console.error("Load Products Error:", err);
    }
}

// --- Actions ---

function setTopupAmount(amount) {
    document.getElementById('topup-amount').value = amount;
}

async function initiateTopup() {
    const amountStr = document.getElementById('topup-amount').value;
    const amount = parseInt(amountStr);

    if (isNaN(amount) || amount < 50 || amount > 50000) {
        tg.showAlert("Please enter a valid amount between 50 and 50,000 ₽.");
        return;
    }

    showOverlay("Creating payment...");

    try {
        const result = await app.currentUser.functions.createPayment(amount, `Top up balance for ${amount} RUB`);
        hideOverlay();

        if (result.success && result.confirmation_url) {
            // Open Yookassa payment page
            tg.openLink(result.confirmation_url);

            // Start polling for payment status
            pollPaymentStatus(result.payment_id);

            tg.showAlert("Please complete the payment in the browser. We will check the status automatically.");
        } else {
            tg.showAlert("Failed to create payment link.");
        }
    } catch (err) {
        hideOverlay();
        console.error("Payment error:", err);
        tg.showAlert("Error initiating payment.");
    }
}

let pollingInterval;
function pollPaymentStatus(paymentId) {
    if (pollingInterval) clearInterval(pollingInterval);

    let attempts = 0;
    pollingInterval = setInterval(async () => {
        attempts++;
        if (attempts > 30) { // Stop after ~5 minutes
            clearInterval(pollingInterval);
            return;
        }

        try {
            const result = await app.currentUser.functions.checkPayment(paymentId);
            if (result.success && result.status === "confirmed") {
                clearInterval(pollingInterval);
                await loadProfile();
                showSuccess("Payment Successful!", result.message);
                switchTab('view-success');
            } else if (result.status === "canceled") {
                 clearInterval(pollingInterval);
                 tg.showAlert("Payment was canceled.");
            }
        } catch (err) {
            console.error("Polling error:", err);
        }
    }, 10000); // Check every 10 seconds
}

async function buySubscription(periodKey, price) {
    // Basic optimistic check (real check is backend)
    const currentBalanceStr = document.getElementById('display-balance').innerText;
    const currentBalance = parseInt(currentBalanceStr.replace(/\D/g,''));

    if (currentBalance < price) {
        tg.showConfirm(`Insufficient balance.\nRequired: ${price} ₽\nAvailable: ${currentBalance} ₽\n\nDo you want to top up?`, (ok) => {
            if (ok) switchTab('view-topup');
        });
        return;
    }

    tg.showConfirm(`Are you sure you want to buy a VPN subscription for ${price} ₽?`, async (ok) => {
        if (!ok) return;

        showOverlay("Processing purchase...");

        try {
            const result = await app.currentUser.functions.buySubscription(periodKey);
            hideOverlay();

            if (result.success) {
                // Update profile data in background
                loadProfile();

                // Show Success screen with config
                document.getElementById('success-title').innerText = "VPN Activated!";
                document.getElementById('success-message').innerText = `Your subscription is active for ${result.config.days} days.`;

                const configDataBox = document.getElementById('success-config-data');
                configDataBox.classList.remove('hidden');
                document.getElementById('success-config-link').value = result.config.link;

                switchTab('view-success');
            }
        } catch (err) {
            hideOverlay();
            console.error("Buy error:", err);
            tg.showAlert(err.message || "Failed to complete purchase.");
        }
    });
}

// --- Utilities ---

function switchTab(viewId) {
    // Hide all views
    document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
    // Show target view
    document.getElementById(viewId).classList.remove('hidden');

    // Update nav colors
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('text-blue-400');
        btn.classList.add('text-gray-400');
    });

    // Highlight active nav
    if (viewId === 'view-dashboard') {
        document.getElementById('nav-dashboard').classList.add('text-blue-400');
        document.getElementById('nav-dashboard').classList.remove('text-gray-400');
        // If coming back to dashboard, hide config block from success screen
        document.getElementById('success-config-data').classList.add('hidden');
    } else if (viewId === 'view-buy') {
        document.getElementById('nav-buy').classList.add('text-blue-400');
        document.getElementById('nav-buy').classList.remove('text-gray-400');
    } else if (viewId === 'view-topup') {
        document.getElementById('nav-topup').classList.add('text-blue-400');
        document.getElementById('nav-topup').classList.remove('text-gray-400');
    }
}

function copyToClipboard(elementId) {
    const copyText = document.getElementById(elementId);
    copyText.select();
    copyText.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(copyText.value);
    tg.showAlert("Config link copied to clipboard!");
}

function copyToClipboardText(text) {
    navigator.clipboard.writeText(text);
    tg.showAlert("Config link copied to clipboard!");
}

function showOverlay(text) {
    document.getElementById('overlay-text').innerText = text;
    document.getElementById('action-overlay').classList.remove('hidden');
}

function hideOverlay() {
    document.getElementById('action-overlay').classList.add('hidden');
}

function showSuccess(title, message) {
    document.getElementById('success-title').innerText = title;
    document.getElementById('success-message').innerText = message;
    document.getElementById('success-config-data').classList.add('hidden'); // hidden by default unless config purchase
    switchTab('view-success');
}

function showError(message) {
    document.getElementById('loading').style.display = 'none';
    const errorScreen = document.getElementById('error-screen');
    document.getElementById('error-message').innerText = message;
    errorScreen.classList.remove('hidden');
}
