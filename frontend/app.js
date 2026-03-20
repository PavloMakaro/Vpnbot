const APP_ID = "vpnbot-app"; // Placeholder, will be replaced by actual App ID

const tg = window.Telegram.WebApp;
tg.expand();

let app;
let currentUser;
let currentProfile = null;
let currentPaymentId = null;
let paymentCheckInterval = null;

// Initialize Realm App
async function initApp() {
    try {
        console.log("Initializing App...");
        app = new Realm.App({ id: APP_ID });

        // Setup theme colors based on Telegram parameters
        document.body.style.backgroundColor = tg.themeParams.bg_color || '#ffffff';
        document.body.style.color = tg.themeParams.text_color || '#000000';

        await login();
        await loadData();

        hideElement('loading');
        showElement('main-content');
    } catch (error) {
        console.error("Initialization error:", error);
        showError("Failed to initialize application. Please try again.");
    }
}

// Authenticate via Custom Function using Telegram initData
async function login() {
    console.log("Logging in...");
    const initData = tg.initData || "dev_bypass_not_allowed";

    // In local development without valid initData, this will fail unless handled
    if (!tg.initData && window.location.hostname !== 'localhost') {
        throw new Error("No Telegram init data found.");
    }

    // Atlas App Services Custom Function Authentication
    const credentials = Realm.Credentials.function({
        initData: initData
    });

    currentUser = await app.logIn(credentials);
    console.log("Logged in user:", currentUser.id);
}

// Load Profile and Configs
async function loadData() {
    console.log("Loading data...");

    try {
        // Fetch profile
        const profileResponse = await currentUser.functions.getProfile();
        if (profileResponse.error) {
            throw new Error(profileResponse.error);
        }

        currentProfile = profileResponse;
        updateUIProfile(currentProfile);

        // Fetch store configurations
        const configsResponse = await currentUser.functions.getConfigs();
        if (configsResponse.error) {
            throw new Error(configsResponse.error);
        }

        renderSubscriptions(configsResponse.periods);

        // Render user's configs
        renderUserConfigs(currentProfile.used_configs);

        // Check active subscription
        const daysLeft = calculateDaysLeft(currentProfile.subscription_end);
        if (daysLeft > 0) {
            const banner = document.getElementById('active-subscription-banner');
            banner.classList.remove('hidden');
            document.getElementById('sub-expires-text').textContent = `Expires in ${daysLeft} days`;
        } else {
             document.getElementById('active-subscription-banner').classList.add('hidden');
        }

    } catch (error) {
         console.error("Data load error:", error);
         showError("Could not load your profile data.");
    }
}

// UI Updates
function updateUIProfile(profile) {
    document.getElementById('user-name').textContent = profile.first_name || profile.username || 'User';
    document.getElementById('user-balance').textContent = `Balance: ${profile.balance || 0} ₽`;

    // Set Initials
    const name = profile.first_name || profile.username || 'U';
    const initials = name.substring(0, 2).toUpperCase();
    document.getElementById('user-avatar').textContent = initials;
}

function renderSubscriptions(periods) {
    const list = document.getElementById('subscriptions-list');
    list.innerHTML = '';

    for (const [key, details] of Object.entries(periods)) {
        const item = document.createElement('div');
        item.className = 'card p-4 flex justify-between items-center bg-white shadow-sm border border-gray-200';
        item.innerHTML = `
            <div>
                <h3 class="font-bold text-lg">${details.days} Days VPN</h3>
                <p class="text-sm text-gray-500">${details.price} ₽</p>
            </div>
            <button onclick="buySubscription('${key}', ${details.price})"
                    class="btn-primary" style="width: auto; padding: 8px 16px;">
                Buy
            </button>
        `;
        list.appendChild(item);
    }
}

function renderUserConfigs(configs) {
    const list = document.getElementById('configs-list');

    if (!configs || configs.length === 0) {
        list.innerHTML = '<div class="text-center py-8 text-gray-500">You don\'t have any active configurations. Purchase a subscription to get started.</div>';
        return;
    }

    list.innerHTML = '';
    configs.reverse().forEach(config => {
        const item = document.createElement('div');
        item.className = 'card p-4 bg-white shadow-sm border border-gray-200';

        // Handle Safari date parsing issue by replacing space with T
        const issueDateStr = config.issue_date.replace(' ', 'T');
        const issueDate = new Date(issueDateStr).toLocaleDateString();

        item.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <h3 class="font-bold text-blue-600">${config.config_name}</h3>
                <span class="text-xs text-gray-400">${issueDate}</span>
            </div>
            <p class="text-sm font-medium mb-1">Period: ${config.period.replace('_', ' ')}</p>
            <div class="mt-2">
                <p class="text-xs text-gray-500 mb-1">Access Link:</p>
                <div class="flex items-center gap-2">
                    <input type="text" readonly value="${config.config_link}" class="text-xs w-full p-2 bg-gray-100 rounded border border-gray-200 text-gray-800" onclick="this.select()">
                    <button onclick="copyToClipboard('${config.config_link}')" class="p-2 bg-blue-100 text-blue-600 rounded hover:bg-blue-200 transition-colors">
                        Copy
                    </button>
                </div>
            </div>
        `;
        list.appendChild(item);
    });
}

// Actions
async function buySubscription(periodKey, price) {
    if (currentProfile.balance < price) {
        tg.showAlert(`Insufficient balance. You need ${price} ₽, but have ${currentProfile.balance} ₽. Please top up.`);
        return;
    }

    tg.showConfirm(`Buy VPN for ${periodKey.replace('_', ' ')} for ${price} ₽?`, async (confirmed) => {
        if (!confirmed) return;

        try {
            tg.MainButton.showProgress(true);
            const response = await currentUser.functions.buySubscription(periodKey);

            if (response.error) {
                 tg.showAlert(response.error);
            } else {
                 tg.showAlert(`Success! Your config link is:\n\n${response.config.link}\n\nIt's also saved in "My Configs".`);
                 await loadData(); // Refresh UI
                 switchTab('configs');
            }
        } catch (error) {
            console.error("Purchase error:", error);
            tg.showAlert("An error occurred during purchase.");
        } finally {
            tg.MainButton.hideProgress();
        }
    });
}

async function topUp(amount) {
    await processTopUp(amount);
}

async function topUpCustom() {
    const input = document.getElementById('custom-amount');
    const amount = parseInt(input.value);

    if (isNaN(amount) || amount < 50 || amount > 50000) {
        tg.showAlert("Please enter an amount between 50 and 50,000 ₽.");
        return;
    }

    input.value = '';
    await processTopUp(amount);
}

async function processTopUp(amount) {
    try {
        tg.MainButton.showProgress(true);
        const response = await currentUser.functions.createPayment(amount, `Top up balance ${amount} RUB`);

        if (response.error) {
            tg.showAlert(response.error);
            return;
        }

        // Open payment URL
        if (response.confirmation_url) {
            tg.openLink(response.confirmation_url);

            // Start checking payment status
            currentPaymentId = response.payment_id;
            startPaymentCheck();
        } else {
             tg.showAlert("Failed to get payment link.");
        }

    } catch (error) {
        console.error("Topup error:", error);
        tg.showAlert("An error occurred while creating the payment.");
    } finally {
        tg.MainButton.hideProgress();
    }
}

// Payment Verification Polling
function startPaymentCheck() {
    if (!currentPaymentId) return;

    showElement('payment-modal');
    document.getElementById('payment-status-text').textContent = "Waiting for payment...";

    // Clear existing interval if any
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
    }

    let attempts = 0;
    const maxAttempts = 60; // 60 attempts * 5 seconds = 5 minutes timeout

    paymentCheckInterval = setInterval(async () => {
        attempts++;
        if (attempts > maxAttempts) {
            stopPaymentCheck("Payment verification timed out. If you paid, it will be credited soon.");
            return;
        }

        try {
            const result = await currentUser.functions.checkPayment(currentPaymentId);

            if (result.status === 'succeeded') {
                stopPaymentCheck("Payment successful! Balance updated.");
                await loadData(); // Refresh balance
            } else if (result.status === 'canceled') {
                stopPaymentCheck("Payment was canceled.");
            }
            // If pending, keep waiting

        } catch (error) {
            console.error("Payment check error:", error);
        }
    }, 5000); // Check every 5 seconds
}

function stopPaymentCheck(message) {
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
        paymentCheckInterval = null;
    }
    hideElement('payment-modal');
    if (message) {
        tg.showAlert(message);
    }
}

// Utilities
function calculateDaysLeft(subscriptionEnd) {
    if (!subscriptionEnd) return 0;

    // Safari date parsing fix
    const endStr = subscriptionEnd.replace(' ', 'T');
    const endDate = new Date(endStr);
    const now = new Date();

    if (endDate <= now) return 0;

    const diffTime = Math.abs(endDate - now);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        tg.showAlert("Copied to clipboard!");
    }).catch(err => {
        console.error('Could not copy text: ', err);
    });
}

// UI Navigation
function switchTab(tabId) {
    // Hide all tabs
    hideElement('store-tab');
    hideElement('configs-tab');

    // Reset tab buttons
    document.getElementById('tab-store').classList.remove('text-blue-500', 'border-b-2', 'border-blue-500');
    document.getElementById('tab-store').classList.add('opacity-70');

    document.getElementById('tab-configs').classList.remove('text-blue-500', 'border-b-2', 'border-blue-500');
    document.getElementById('tab-configs').classList.add('opacity-70');

    // Show selected tab
    showElement(`${tabId}-tab`);

    // Highlight selected tab button
    const activeBtn = document.getElementById(`tab-${tabId}`);
    activeBtn.classList.remove('opacity-70');
    activeBtn.classList.add('text-blue-500', 'border-b-2', 'border-blue-500');
}

function hideElement(id) {
    document.getElementById(id).classList.add('hidden');
}

function showElement(id) {
    document.getElementById(id).classList.remove('hidden');
}

function showError(message) {
    hideElement('loading');
    hideElement('main-content');
    showElement('error-screen');
    document.getElementById('error-message').textContent = message;
}

// Ensure the Telegram Main Button is hidden initially
tg.MainButton.hide();

// Start application
initApp();