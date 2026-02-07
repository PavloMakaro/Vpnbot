// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Realm App Configuration
// REPLACE 'application-0-xyz' WITH YOUR ACTUAL APP ID
const APP_ID = 'application-0-xyz';
const app = new Realm.App({ id: APP_ID });

// Global State
let user = null;
let userData = {};

// UI Helper Functions
function showLoading() {
    document.getElementById('loading-screen').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading-screen').classList.add('hidden');
}

function showMain() {
    document.getElementById('main-content').classList.remove('hidden');
    hideLoading();
}

function showSection(sectionId) {
    document.getElementById(`section-${sectionId}`).classList.remove('hidden');
    tg.BackButton.show();

    if (sectionId === 'plans') loadPlans();
    if (sectionId === 'configs') loadConfigs();
}

function hideSection(sectionId) {
    document.getElementById(`section-${sectionId}`).classList.add('hidden');
    tg.BackButton.hide();
}

tg.BackButton.onClick(() => {
    ['topup', 'plans', 'configs'].forEach(id => {
        if (!document.getElementById(`section-${id}`).classList.contains('hidden')) {
            hideSection(id);
        }
    });
});

// Authentication & Initialization
async function initApp() {
    try {
        if (!tg.initData) {
            console.error("No Telegram initData found. Are you running inside Telegram?");
            // For testing outside Telegram, you might want to mock initData
        }

        // Authenticate with Stitch using Custom Function Auth
        const credentials = Realm.Credentials.function({
            initData: tg.initData
        });

        user = await app.logIn(credentials);
        console.log("Logged in user:", user.id);

        await loadUserProfile();
        showMain();

    } catch (err) {
        console.error("Failed to log in", err);
        alert("Authentication failed. Please try again.");
    }
}

// Data Fetching
async function loadUserProfile() {
    try {
        // Call backend function 'getProfile'
        userData = await user.functions.getProfile();

        document.getElementById('user-name').textContent = userData.first_name;
        document.getElementById('user-id').textContent = `ID: ${userData.user_id}`;
        document.getElementById('user-balance').textContent = `${userData.balance} ₽`;

        const subEnd = userData.subscription_end;
        const subStatusEl = document.getElementById('sub-status');

        if (subEnd && new Date(subEnd) > new Date()) {
            const date = new Date(subEnd).toLocaleDateString();
            subStatusEl.textContent = `Active until ${date}`;
            subStatusEl.classList.remove('text-red-400');
            subStatusEl.classList.add('text-green-400');
        } else {
            subStatusEl.textContent = 'Inactive';
            subStatusEl.classList.remove('text-green-400');
            subStatusEl.classList.add('text-red-400');
        }

        // Update user avatar logic if needed (Telegram doesn't send avatar URL in initDataUnsafe consistently for bot web apps, but we can use first letter)
        const initial = userData.first_name ? userData.first_name[0].toUpperCase() : '?';
        document.getElementById('user-avatar').textContent = initial;

    } catch (err) {
        console.error("Failed to load profile", err);
    }
}

async function loadPlans() {
    const container = document.getElementById('plans-container');
    container.innerHTML = '<div class="text-center text-gray-500 mt-10">Loading plans...</div>';

    try {
        const plans = await user.functions.getPlans();
        container.innerHTML = '';

        if (plans.length === 0) {
            container.innerHTML = '<div class="text-center text-gray-500">No plans available</div>';
            return;
        }

        plans.forEach(plan => {
            const div = document.createElement('div');
            div.className = 'bg-gray-800 p-4 rounded-lg flex justify-between items-center';
            div.innerHTML = `
                <div>
                    <h3 class="font-bold">${plan.days} Days</h3>
                    <p class="text-sm text-gray-400">Premium VPN Access</p>
                </div>
                <div class="flex items-center space-x-3">
                    <span class="font-bold text-lg">${plan.price} ₽</span>
                    <button onclick="buySubscription('${plan.id}')" class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-bold">
                        Buy
                    </button>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (err) {
        console.error("Failed to load plans", err);
        container.innerHTML = '<div class="text-center text-red-500">Error loading plans</div>';
    }
}

async function loadConfigs() {
    const container = document.getElementById('configs-container');
    container.innerHTML = '<div class="text-center text-gray-500 mt-10">Loading configs...</div>';

    try {
        const configs = await user.functions.getMyConfigs();
        container.innerHTML = '';

        if (configs.length === 0) {
            container.innerHTML = '<div class="text-center text-gray-500">You have no active configs. Buy a subscription first!</div>';
            return;
        }

        configs.forEach(config => {
            const div = document.createElement('div');
            div.className = 'bg-gray-800 p-4 rounded-lg mb-3';
            div.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <div>
                        <h3 class="font-bold text-blue-400">${config.config_name}</h3>
                        <p class="text-xs text-gray-400">Valid until: ${config.expiry_date || 'N/A'}</p>
                    </div>
                </div>
                <div class="bg-gray-900 p-2 rounded text-xs text-gray-300 break-all font-mono select-all cursor-pointer" onclick="copyToClipboard(this)">
                    ${config.config_link}
                </div>
                <p class="text-xs text-gray-500 mt-1 text-center">Tap link to copy</p>
            `;
            container.appendChild(div);
        });
    } catch (err) {
        console.error("Failed to load configs", err);
        container.innerHTML = '<div class="text-center text-red-500">Error loading configs</div>';
    }
}

// Actions
function selectAmount(amount) {
    document.getElementById('custom-amount').value = amount;
}

async function initiatePayment() {
    const amountInput = document.getElementById('custom-amount');
    const amount = parseInt(amountInput.value);

    if (!amount || amount < 50) {
        tg.showAlert("Minimum amount is 50 ₽");
        return;
    }

    try {
        tg.MainButton.showProgress();
        const result = await user.functions.createPayment({ amount });
        tg.MainButton.hideProgress();

        if (result.confirmation_url) {
            tg.openLink(result.confirmation_url);
            tg.close(); // Optional: close app so user sees the payment in browser, or keep open
        } else {
            tg.showAlert("Failed to create payment link.");
        }
    } catch (err) {
        console.error("Payment error", err);
        tg.MainButton.hideProgress();
        tg.showAlert("An error occurred. Please try again.");
    }
}

async function buySubscription(planId) {
    if (!confirm("Are you sure you want to buy this subscription?")) return;

    try {
        showLoading();
        const result = await user.functions.buySubscription({ planId });

        if (result.success) {
            tg.showAlert("Subscription purchased successfully!");
            await loadUserProfile(); // Refresh balance
            hideSection('plans');
            showSection('configs'); // Show the new config
        } else {
            tg.showAlert(result.message || "Failed to purchase subscription.");
        }
        hideLoading();
    } catch (err) {
        console.error("Purchase error", err);
        hideLoading();
        tg.showAlert("An error occurred: " + err.message);
    }
}

function copyToClipboard(element) {
    const text = element.innerText;
    navigator.clipboard.writeText(text).then(() => {
        tg.showPopup({ message: "Config link copied to clipboard!" });
    });
}

// Start
window.addEventListener('load', initApp);
