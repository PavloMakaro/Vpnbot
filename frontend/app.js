// --- Configuration ---
const APP_ID = "application-0-huxrmqf"; // Replace with your actual Realm App ID
const app = new Realm.App({ id: APP_ID });

// --- UI Elements ---
const elUserGreeting = document.getElementById('user-greeting');
const elUserBalance = document.getElementById('user-balance');
const elStatusIndicator = document.getElementById('status-indicator');
const elStatusText = document.getElementById('status-text');
const elSubscriptionDate = document.getElementById('subscription-date');
const elSubscriptionPlans = document.getElementById('subscription-plans');
const elConfigsList = document.getElementById('configs-list');

const tabBuy = document.getElementById('tab-buy');
const tabConfigs = document.getElementById('tab-configs');
const sectionBuy = document.getElementById('section-buy');
const sectionConfigs = document.getElementById('section-configs');
const overlay = document.getElementById('loading-overlay');
const overlayText = document.getElementById('loading-text');

let currentUserProfile = null;

// --- Telegram WebApp Integration ---
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

// --- Initialization ---
async function init() {
    showLoading("Connecting to server...");
    try {
        // 1. Authenticate with Realm using Telegram initData
        const initData = tg.initData || "mock_init_data"; // Fallback for local testing if needed

        if (!app.currentUser) {
            // Using Custom Function Authentication
            const credentials = Realm.Credentials.function({ initData: initData });
            await app.logIn(credentials);
        }

        // 2. Fetch Profile and Configs
        await loadData();

        hideLoading();
    } catch (err) {
        console.error("Initialization failed:", err);
        tg.showAlert("Failed to initialize app. Please try again.");
        hideLoading();
    }
}

async function loadData() {
    if (!app.currentUser) return;

    try {
        // Run checks in parallel
        const [profile, plans] = await Promise.all([
            app.currentUser.functions.getProfile(),
            app.currentUser.functions.getConfigs()
        ]);

        currentUserProfile = profile;

        // Update UI
        updateProfileUI(profile);
        renderPlans(plans);
        renderConfigs(profile.used_configs || []);

        // Also proactively check for pending payments
        app.currentUser.functions.checkPendingPayments()
            .then(res => {
                if(res.checked > 0) {
                     // Reload profile if payments were checked, just in case balance changed
                    app.currentUser.functions.getProfile().then(p => {
                        currentUserProfile = p;
                        updateProfileUI(p);
                    });
                }
            })
            .catch(console.error);

    } catch (err) {
        console.error("Error loading data:", err);
        tg.showAlert("Failed to load your data.");
    }
}

// --- UI Updaters ---

function updateProfileUI(profile) {
    elUserGreeting.textContent = `Hello, ${profile.first_name}!`;
    elUserBalance.textContent = profile.balance || 0;

    const subEnd = profile.subscription_end ? new Date(profile.subscription_end.replace(' ', 'T')) : null;
    const now = new Date();

    if (subEnd && subEnd > now) {
        elStatusIndicator.className = "inline-block w-3 h-3 rounded-full bg-green-500";

        const daysLeft = Math.ceil((subEnd - now) / (1000 * 60 * 60 * 24));
        elStatusText.textContent = `Active (${daysLeft} days left)`;
        elStatusText.className = "text-green-600 font-medium";

        elSubscriptionDate.textContent = `Valid until: ${subEnd.toLocaleDateString()}`;
        elSubscriptionDate.classList.remove('hidden');
    } else {
        elStatusIndicator.className = "inline-block w-3 h-3 rounded-full bg-red-500";
        elStatusText.textContent = "Inactive";
        elStatusText.className = "text-red-600 font-medium";
        elSubscriptionDate.classList.add('hidden');
    }
}

function renderPlans(plans) {
    elSubscriptionPlans.innerHTML = '';

    // Sort plans by price
    const sortedPlans = Object.entries(plans).sort((a, b) => a[1].price - b[1].price);

    sortedPlans.forEach(([periodKey, data]) => {
        const div = document.createElement('div');
        div.className = "flex justify-between items-center border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors";

        div.innerHTML = `
            <div>
                <p class="font-medium text-gray-800">${data.days} Days</p>
                <p class="text-sm text-gray-500">${data.price} ₽</p>
            </div>
            <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition-colors" onclick="buySubscription('${periodKey}', ${data.price})">
                Buy
            </button>
        `;
        elSubscriptionPlans.appendChild(div);
    });
}

function renderConfigs(configs) {
    elConfigsList.innerHTML = '';

    if (!configs || configs.length === 0) {
        elConfigsList.innerHTML = '<div class="text-center text-gray-500 py-8">No configs found. Buy a subscription to get one.</div>';
        return;
    }

    // Reverse to show newest first
    const reversedConfigs = [...configs].reverse();

    reversedConfigs.forEach(cfg => {
        const div = document.createElement('div');
        div.className = "bg-white border border-gray-200 rounded-lg p-4 shadow-sm";

        div.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <h4 class="font-medium text-gray-800">${cfg.config_name}</h4>
                <span class="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">${cfg.period}</span>
            </div>
            <p class="text-xs text-gray-500 mb-3">Issued: ${cfg.issue_date}</p>

            <div class="bg-gray-50 p-2 rounded border border-gray-200 flex items-center justify-between overflow-hidden">
                <code class="text-xs text-gray-600 truncate mr-2 select-all">${cfg.config_link}</code>
                <button class="text-blue-600 hover:text-blue-800 p-1 flex-shrink-0" onclick="copyToClipboard('${cfg.config_link}')" title="Copy to clipboard">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                </button>
            </div>
        `;
        elConfigsList.appendChild(div);
    });
}

// --- Actions ---

async function topUp(amount) {
    if (!amount || amount < 50) {
        tg.showAlert("Minimum top-up amount is 50 ₽");
        return;
    }

    showLoading("Creating payment...");
    try {
        const returnUrl = window.location.href;
        const result = await app.currentUser.functions.createPayment(amount, returnUrl);

        if (result && result.confirmation_url) {
            // Open payment URL in Telegram browser
            tg.openLink(result.confirmation_url);

            // Show alert instructing user to return
            tg.showAlert("Please complete the payment in the browser, then return here.", () => {
                // When they close the alert, check payment status
                showLoading("Verifying payment...");
                app.currentUser.functions.checkPayment(result.payment_id)
                    .then(verifyRes => {
                        if (verifyRes.status === "succeeded") {
                            tg.showAlert("Payment successful! Balance updated.");
                            loadData(); // Reload profile to get new balance
                        } else {
                            tg.showAlert(`Payment status: ${verifyRes.status}. If you paid, please wait a moment and reload the app.`);
                        }
                    })
                    .catch(err => {
                        console.error("Verification error:", err);
                        tg.showAlert("Failed to verify payment immediately. Your balance will be updated automatically soon.");
                    })
                    .finally(hideLoading);
            });
        }
    } catch (err) {
        console.error("Top-up failed:", err);
        tg.showAlert("Failed to create payment: " + err.message);
        hideLoading();
    }
}

async function buySubscription(periodKey, price) {
    if (!currentUserProfile) return;

    if (currentUserProfile.balance < price) {
        tg.showAlert(`Insufficient funds. You need ${price} ₽, but have ${currentUserProfile.balance} ₽. Please top up your balance.`);
        // Switch to buy tab automatically
        switchTab('buy');
        return;
    }

    tg.showConfirm(`Purchase ${periodKey.replace('_', ' ')} subscription for ${price} ₽?`, async (confirmed) => {
        if (!confirmed) return;

        showLoading("Processing purchase...");
        try {
            const result = await app.currentUser.functions.buySubscription(periodKey);
            if (result.success) {
                tg.showAlert("Subscription purchased successfully! Your config is ready.");
                await loadData(); // Reload profile to show new config and balance
                switchTab('configs'); // Switch to configs tab to show it
            }
        } catch (err) {
            console.error("Purchase failed:", err);
            tg.showAlert(err.message || "Failed to purchase subscription.");
        } finally {
            hideLoading();
        }
    });
}

// --- Helpers ---

function switchTab(tabName) {
    if (tabName === 'buy') {
        tabBuy.className = "flex-1 py-3 text-center font-medium bg-blue-50 text-blue-600 border-b-2 border-blue-600 transition-colors";
        tabConfigs.className = "flex-1 py-3 text-center font-medium text-gray-500 hover:bg-gray-50 border-b-2 border-transparent transition-colors";
        sectionBuy.classList.remove('hidden');
        sectionConfigs.classList.add('hidden');
    } else {
        tabConfigs.className = "flex-1 py-3 text-center font-medium bg-blue-50 text-blue-600 border-b-2 border-blue-600 transition-colors";
        tabBuy.className = "flex-1 py-3 text-center font-medium text-gray-500 hover:bg-gray-50 border-b-2 border-transparent transition-colors";
        sectionConfigs.classList.remove('hidden');
        sectionBuy.classList.add('hidden');
    }
}

function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            tg.HapticFeedback.impactOccurred('light');

            // Temporary visual feedback
            const toast = document.createElement('div');
            toast.className = "fixed bottom-5 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white px-4 py-2 rounded-full text-sm shadow-lg z-50 fade-in";
            toast.textContent = "Copied to clipboard!";
            document.body.appendChild(toast);

            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }, 2000);
        });
    } else {
        // Fallback
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "absolute";
        textArea.style.left = "-999999px";
        document.body.prepend(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            tg.HapticFeedback.impactOccurred('light');
            tg.showAlert("Copied to clipboard!");
        } catch (error) {
            console.error(error);
        } finally {
            textArea.remove();
        }
    }
}

function showLoading(text = "Processing...") {
    overlayText.textContent = text;
    overlay.classList.remove('hidden');
}

function hideLoading() {
    overlay.classList.add('hidden');
}

// --- Event Listeners ---

tabBuy.addEventListener('click', () => switchTab('buy'));
tabConfigs.addEventListener('click', () => switchTab('configs'));

document.querySelectorAll('.topup-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const amount = parseInt(e.target.dataset.amount);
        topUp(amount);
    });
});

document.getElementById('btn-topup-custom').addEventListener('click', () => {
    const amount = parseInt(document.getElementById('custom-amount').value);
    topUp(amount);
});

// --- Boot ---
// Small delay to ensure Telegram WebApp is fully ready
setTimeout(init, 100);
