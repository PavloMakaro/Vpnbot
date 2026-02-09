// CONFIGURATION
const APP_ID = "application-0-xyz"; // REPLACE WITH YOUR REALM APP ID

// Initialize SDKs
const app = new Realm.App({ id: APP_ID });
const tg = window.Telegram.WebApp;

// Expand to full height
tg.expand();

// State
let currentUser = null;
let userProfile = null;

// Initialization
async function init() {
    try {
        console.log("Initializing app...");

        // Check if initData is available (it should be in Mini App)
        // If testing in browser without Telegram, use a mock or handle error
        const initData = tg.initData;

        if (!initData) {
            console.warn("No initData found. Are you running in Telegram?");
            // For development purposes, you might want to allow anonymous login or mock data
            // But for this production-ready code, we'll try to log in with what we have
        }

        // Authenticate with Realm using Custom Function Auth
        // The function 'auth' in Stitch will validate the initData
        const credentials = Realm.Credentials.function({
            initData: initData
        });

        currentUser = await app.logIn(credentials);
        console.log("Logged in user:", currentUser.id);

        // Fetch profile data
        await fetchProfile();

        // Hide loader and show home
        document.getElementById('loader').classList.add('hidden');
        navigate('home');

        // Setup MainButton for payments/actions if needed, or hide it initially
        tg.MainButton.hide();

    } catch (err) {
        console.error("Login failed:", err);
        document.getElementById('loader').innerHTML = `
            <div class="text-red-500">
                <p class="font-bold">Login Failed</p>
                <p class="text-sm">${err.message}</p>
                <p class="text-xs mt-4">Make sure you are opening this from Telegram.</p>
            </div>
        `;
    }
}

// Data Fetching
async function fetchProfile() {
    try {
        // Call the 'getUserProfile' Atlas Function
        userProfile = await currentUser.functions.getUserProfile();
        renderProfile();
    } catch (err) {
        console.error("Failed to fetch profile:", err);
        tg.showAlert("Failed to load profile data.");
    }
}

// UI Rendering
function renderProfile() {
    if (!userProfile) return;

    // Header Info
    document.getElementById('user-name').innerText = userProfile.first_name || "User";
    document.getElementById('user-balance').innerText = `${userProfile.balance} ₽`;

    // Subscription Details
    const subContainer = document.getElementById('subscription-details');
    if (userProfile.days_left > 0) {
        const endDate = new Date(userProfile.subscription_end).toLocaleDateString();
        subContainer.innerHTML = `
            <div class="flex items-center text-green-600 mb-1">
                <span class="text-2xl mr-2">✅</span>
                <span class="font-bold">Active</span>
            </div>
            <p class="text-gray-600 dark:text-gray-400 text-sm">
                ${userProfile.days_left} days left (until ${endDate})
            </p>
        `;
    } else {
        subContainer.innerHTML = `
            <div class="flex items-center text-red-500 mb-1">
                <span class="text-2xl mr-2">❌</span>
                <span class="font-bold">Inactive</span>
            </div>
            <p class="text-gray-600 dark:text-gray-400 text-sm">
                Access to VPN is disabled.
            </p>
        `;
    }

    // Referral Link
    const refLink = `https://t.me/vpni50_bot?start=${userProfile._id}`;
    document.getElementById('referral-link').innerText = refLink;
}

// Navigation
function navigate(viewId) {
    // Hide all views
    const views = ['home', 'shop', 'configs', 'topup', 'referral'];
    views.forEach(v => {
        document.getElementById(`view-${v}`).classList.add('hidden');
        const navBtn = document.getElementById(`nav-${v}`);
        if (navBtn) navBtn.classList.remove('text-blue-500');
    });

    // Show target view
    const target = document.getElementById(`view-${viewId}`);
    if (target) {
        target.classList.remove('hidden');
        window.scrollTo(0,0);
    }

    // Update Nav Bar
    const navBtn = document.getElementById(`nav-${viewId}`);
    if (navBtn) navBtn.classList.add('text-blue-500');

    // Trigger specific actions
    if (viewId === 'configs') {
        fetchConfigs();
    }

    // Back button logic
    if (viewId === 'home') {
        tg.BackButton.hide();
    } else {
        tg.BackButton.show();
        tg.BackButton.onClick(() => navigate('home'));
    }
}

// Actions
async function buySubscription(planId) {
    const plans = {
        '1_month': '1 Month (50 RUB)',
        '2_months': '2 Months (90 RUB)',
        '3_months': '3 Months (120 RUB)'
    };

    const planName = plans[planId] || planId;

    tg.showConfirm(`Purchase ${planName}?`, async (confirmed) => {
        if (confirmed) {
            try {
                tg.MainButton.showProgress();
                const result = await currentUser.functions.buySubscription(planId);
                tg.MainButton.hideProgress();

                if (result.success) {
                    tg.showAlert("Subscription purchased successfully!");
                    await fetchProfile();
                    navigate('home');
                }
            } catch (err) {
                tg.MainButton.hideProgress();
                tg.showAlert(err.message); // Show error from backend (e.g. Insufficient funds)
                if (err.message.includes("Insufficient balance")) {
                    navigate('topup');
                }
            }
        }
    });
}

async function initiatePayment() {
    const amountInput = document.getElementById('topup-amount');
    const amount = parseFloat(amountInput.value);

    if (!amount || amount < 50) {
        tg.showAlert("Minimum amount is 50 RUB");
        return;
    }

    try {
        tg.MainButton.setText("Generating Payment...");
        tg.MainButton.show();
        tg.MainButton.showProgress();

        const paymentUrl = await currentUser.functions.createPayment(amount, "Balance topup", null);

        tg.MainButton.hideProgress();
        tg.MainButton.hide();

        // Open payment
        tg.openLink(paymentUrl);

    } catch (err) {
        tg.MainButton.hideProgress();
        tg.MainButton.hide();
        tg.showAlert("Error: " + err.message);
    }
}

async function fetchConfigs() {
    const container = document.getElementById('configs-container');
    container.innerHTML = '<p class="text-center text-gray-500 mt-4">Loading configs...</p>';

    try {
        const configs = await currentUser.functions.getConfigs();

        if (!configs || configs.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8">
                    <p class="text-gray-500 mb-4">You don't have any configs yet.</p>
                    <button onclick="navigate('shop')" class="text-blue-500 font-medium">Buy Subscription</button>
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        configs.forEach((config, index) => {
            const card = document.createElement('div');
            card.className = 'bg-secondary p-4 rounded-lg shadow-sm mb-3';
            card.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-sm">${config.config_name}</h3>
                    <span class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">${config.period}</span>
                </div>
                <p class="text-xs text-gray-500 mb-3">Issued: ${new Date(config.issue_date).toLocaleDateString()}</p>

                <div class="bg-white dark:bg-gray-800 p-2 rounded border border-gray-200 dark:border-gray-600 mb-3 relative group">
                    <code class="text-xs break-all block max-h-24 overflow-hidden text-gray-600 dark:text-gray-300 font-mono">
                        ${config.config_link.substring(0, 100)}...
                    </code>
                    <div class="absolute inset-0 bg-gradient-to-t from-white dark:from-gray-800 to-transparent"></div>
                </div>

                <button class="w-full bg-blue-500 text-white py-2 rounded text-sm font-medium hover:bg-blue-600 transition"
                    onclick="copyConfig('${config.config_link}')">
                    Copy VLESS/Vmess Link
                </button>
            `;
            container.appendChild(card);
        });

    } catch (err) {
        console.error("Fetch configs error:", err);
        container.innerHTML = `<p class="text-center text-red-500 mt-4">Failed to load configs.</p>`;
    }
}

function copyConfig(link) {
    navigator.clipboard.writeText(link).then(() => {
        tg.showAlert("Config link copied to clipboard!");
    }).catch(err => {
        tg.showAlert("Failed to copy.");
    });
}

function copyReferralLink() {
    const link = document.getElementById('referral-link').innerText;
    navigator.clipboard.writeText(link).then(() => {
        tg.showAlert("Referral link copied!");
    });
}

// Start the app
document.addEventListener('DOMContentLoaded', init);
