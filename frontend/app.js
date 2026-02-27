// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();
tg.enableClosingConfirmation();

// Realm App ID (Replace with your actual Realm App ID from MongoDB Atlas)
// For now, using a placeholder. The user MUST update this.
const REALM_APP_ID = "vpn-bot-xyz";
const app = new Realm.App({ id: REALM_APP_ID });

// Global state
let currentUser = null;
let userData = {};

// Main function
async function init() {
    try {
        if (!tg.initData) {
            console.error("No initData available. Are you running in Telegram?");
            // For testing outside Telegram, you might mock this or show an error
        }

        // Authenticate with Realm using Custom Function Auth
        // The auth function on backend expects the initData string
        const credentials = Realm.Credentials.function({
            initData: tg.initData
        });

        currentUser = await app.logIn(credentials);
        console.log("Logged in user:", currentUser.id);

        await loadProfile();
        await loadConfigs(); // Load available plans to buy
        await loadUserConfigs(); // Load user's purchased configs

    } catch (err) {
        console.error("Failed to login:", err);
        showToast("Authentication failed. Please restart the bot.");
    }
}

async function loadProfile() {
    try {
        userData = await currentUser.functions.getProfile();

        document.getElementById('username').innerText = `@${userData.username}`;
        document.getElementById('balance').innerText = `${userData.balance} ₽`;

        const subEnd = userData.subscription_end ? new Date(userData.subscription_end) : null;
        if (subEnd && subEnd > new Date()) {
            const daysLeft = Math.ceil((subEnd - new Date()) / (1000 * 60 * 60 * 24));
            document.getElementById('subscription-status').innerHTML = `<span class="text-green-400">Active (${daysLeft} days left)</span>`;
        } else {
            document.getElementById('subscription-status').innerHTML = `<span class="text-red-400">Inactive</span>`;
        }

        document.getElementById('referral-count').innerText = userData.referrals_count;

        // Referral Link
        const botUsername = "vpni50_bot"; // Replace with your bot username
        const refLink = `https://t.me/${botUsername}?start=${currentUser.id}`;
        document.getElementById('referral-link').innerText = refLink;

        document.getElementById('copy-ref-btn').onclick = () => {
             navigator.clipboard.writeText(refLink);
             showToast("Referral link copied!");
        };

    } catch (e) {
        console.error("Error loading profile:", e);
        showToast("Failed to load profile.");
    }
}

async function loadConfigs() {
    try {
        const plans = await currentUser.functions.getConfigs();
        const container = document.getElementById('plans-container');
        container.innerHTML = '';

        for (const [key, plan] of Object.entries(plans)) {
            const card = document.createElement('div');
            card.className = "bg-gray-700 p-4 rounded-lg flex justify-between items-center plan-card cursor-pointer";
            card.innerHTML = `
                <div>
                    <h3 class="font-bold text-lg">${plan.days} Days</h3>
                    <p class="text-sm text-gray-400">${plan.price} ₽</p>
                </div>
                <button class="bg-blue-600 hover:bg-blue-500 text-white font-bold py-1 px-3 rounded text-sm transition" onclick="buySubscription('${key}')">
                    Buy
                </button>
            `;
            container.appendChild(card);
        }
    } catch (e) {
        console.error("Error loading plans:", e);
    }
}

async function buySubscription(periodKey) {
    if (!confirm("Are you sure you want to buy this subscription?")) return;

    // Show loading on button (simplified)
    showToast("Processing purchase...");

    try {
        const result = await currentUser.functions.buySubscription(periodKey);

        if (result.success) {
            showToast("Subscription purchased successfully!");
            // Refresh profile and configs
            await loadProfile();
            await loadUserConfigs();
        }
    } catch (e) {
        console.error("Purchase failed:", e);
        showToast(`Error: ${e.message || "Purchase failed"}`);
    }
}

async function loadUserConfigs() {
    try {
        // We get used_configs from getProfile, but let's re-fetch or use userData
        // Ideally getProfile should be called again to refresh
        const container = document.getElementById('configs-list');
        container.innerHTML = '';

        if (!userData.used_configs || userData.used_configs.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center">No active configs found.</p>';
            return;
        }

        // Show latest first
        const reversedConfigs = [...userData.used_configs].reverse();

        reversedConfigs.forEach(conf => {
            const item = document.createElement('div');
            item.className = "bg-gray-700 p-3 rounded config-item mb-2";
            item.innerHTML = `
                <div class="flex justify-between items-start">
                    <div>
                        <h4 class="font-bold text-sm">${conf.config_name}</h4>
                        <p class="text-xs text-gray-400">Issued: ${new Date(conf.issue_date).toLocaleDateString()}</p>
                    </div>
                    <button onclick="copyConfig('${conf.config_link}')" class="text-blue-400 text-xs hover:text-white">
                        <i class="far fa-copy"></i> Copy Link
                    </button>
                </div>
                <div class="mt-2 bg-gray-800 p-2 rounded text-xs text-gray-300 font-mono break-all cursor-pointer hover:bg-gray-900 transition" onclick="copyConfig('${conf.config_link}')">
                    ${conf.config_link.substring(0, 40)}...
                </div>
            `;
            container.appendChild(item);
        });

    } catch (e) {
        console.error("Error loading user configs:", e);
    }
}

window.copyConfig = (link) => {
    navigator.clipboard.writeText(link);
    showToast("Config link copied!");
};

// Top Up Button Logic
document.getElementById('btn-topup').addEventListener('click', async () => {
    const amountStr = prompt("Enter amount to top up (RUB):", "100");
    if (!amountStr) return;

    const amount = parseFloat(amountStr);
    if (isNaN(amount) || amount < 50) {
        showToast("Minimum amount is 50 RUB");
        return;
    }

    showToast("Creating payment...");
    try {
        const result = await currentUser.functions.createPayment(amount);
        if (result.confirmation_url) {
            // Open payment link
            tg.openLink(result.confirmation_url);

            // Poll for payment status
            checkPaymentStatus(result.payment_id);
        }
    } catch (e) {
        console.error("Topup error:", e);
        showToast("Failed to create payment.");
    }
});

async function checkPaymentStatus(paymentId) {
    let attempts = 0;
    const maxAttempts = 20; // 20 * 3s = 60s polling

    const interval = setInterval(async () => {
        attempts++;
        if (attempts >= maxAttempts) {
            clearInterval(interval);
            return;
        }

        try {
            const status = await currentUser.functions.checkPayment(paymentId);
            if (status.status === 'succeeded') {
                clearInterval(interval);
                showToast("Payment successful! Balance updated.");
                loadProfile();
            } else if (status.status === 'canceled') {
                clearInterval(interval);
                showToast("Payment canceled.");
            }
        } catch (e) {
            console.error("Check payment error:", e);
        }
    }, 3000);
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.innerText = message;
    toast.classList.remove('opacity-0', 'pointer-events-none');
    toast.classList.add('opacity-100');

    setTimeout(() => {
        toast.classList.remove('opacity-100');
        toast.classList.add('opacity-0', 'pointer-events-none');
    }, 3000);
}

// Start app
init();
