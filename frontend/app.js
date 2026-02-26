const APP_ID = "YOUR_REALM_APP_ID"; // Replace with your actual Realm App ID
const app = new Realm.App({ id: APP_ID });

const tg = window.Telegram.WebApp;
tg.expand();

// Helper to show/hide loading
function setLoading(show) {
    const el = document.getElementById('loading');
    if (show) el.classList.remove('hidden');
    else el.classList.add('hidden');
}

// Helper to switch tabs
window.switchTab = function(tab) {
    const buyTab = document.getElementById('tab-buy');
    const configsTab = document.getElementById('tab-configs');
    const buySection = document.getElementById('section-buy');
    const configsSection = document.getElementById('section-configs');

    if (tab === 'buy') {
        buyTab.classList.add('text-blue-400', 'border-b-2', 'border-blue-400');
        buyTab.classList.remove('text-gray-400');
        configsTab.classList.remove('text-blue-400', 'border-b-2', 'border-blue-400');
        configsTab.classList.add('text-gray-400');

        buySection.classList.remove('hidden');
        configsSection.classList.add('hidden');
    } else {
        configsTab.classList.add('text-blue-400', 'border-b-2', 'border-blue-400');
        configsTab.classList.remove('text-gray-400');
        buyTab.classList.remove('text-blue-400', 'border-b-2', 'border-blue-400');
        buyTab.classList.add('text-gray-400');

        buySection.classList.add('hidden');
        configsSection.classList.remove('hidden');
        loadConfigs();
    }
}

// Initialization
async function init() {
    setLoading(true);
    try {
        if (!tg.initData) {
            console.warn("No initData found. Running in test mode?");
        }

        // Login
        // Note: For Custom Function Auth, payload key depends on provider configuration.
        // Usually it's just the argument to the function.
        // If the provider expects specific fields, adjust here.
        // Assuming provider passes the argument as 'loginPayload' to the function.
        const credentials = Realm.Credentials.function({ initData: tg.initData });
        const user = await app.logIn(credentials);
        console.log("Logged in:", user.id);

        // Fetch Profile
        await loadProfile();

    } catch (err) {
        console.error("Init error:", err);
        // Don't alert immediately in prod if initData is missing, maybe show login screen
        if (tg.initData) alert("Error initializing app: " + err.message);
    } finally {
        setLoading(false);
    }
}

async function loadProfile() {
    const user = app.currentUser;
    if (!user) return;

    // Call getProfile function
    const startParam = tg.initDataUnsafe?.start_param;
    try {
        const profile = await user.functions.getProfile({
            username: tg.initDataUnsafe?.user?.username,
            first_name: tg.initDataUnsafe?.user?.first_name,
            start_param: startParam
        });

        document.getElementById('user-name').textContent = profile.first_name || 'User';
        document.getElementById('user-id').textContent = profile._id;
        document.getElementById('user-balance').textContent = profile.balance;
        // Avatar placeholder (first letter)
        const initial = (profile.first_name || 'U')[0].toUpperCase();
        document.getElementById('user-avatar').textContent = initial;

        // Sub Status
        const subStatusEl = document.getElementById('sub-status');
        const subDateEl = document.getElementById('sub-date');

        if (profile.subscription_end) {
            const endDate = new Date(profile.subscription_end);
            if (endDate > new Date()) {
                subStatusEl.textContent = "Active";
                subStatusEl.classList.remove('text-red-400');
                subStatusEl.classList.add('text-green-400');
                subDateEl.textContent = `Expires: ${endDate.toLocaleDateString()}`;
                subDateEl.classList.remove('hidden');
            } else {
                subStatusEl.textContent = "Expired";
                subStatusEl.classList.remove('text-green-400');
                subStatusEl.classList.add('text-red-400');
                subDateEl.classList.add('hidden');
            }
        }
    } catch (e) {
        console.error("Load profile failed", e);
    }
}

window.buySubscription = async function(period) {
    if (!confirm("Are you sure you want to buy this subscription?")) return;

    setLoading(true);
    const user = app.currentUser;
    try {
        const result = await user.functions.buySubscription(period);
        if (result.success) {
            alert("Subscription purchased successfully!");
            await loadProfile();
            switchTab('configs'); // Switch to configs tab to show it
        }
    } catch (err) {
        alert("Purchase failed: " + err.message);
    } finally {
        setLoading(false);
    }
};

window.setTopUp = function(amount) {
    document.getElementById('topup-amount').value = amount;
}

window.topUp = async function() {
    const amount = parseFloat(document.getElementById('topup-amount').value);
    if (!amount || amount < 10) {
        alert("Please enter a valid amount (min 10 RUB).");
        return;
    }

    setLoading(true);
    const user = app.currentUser;
    try {
        const url = await user.functions.createPayment(amount, "Balance Top-up");
        // Open payment URL
        tg.openLink(url);

        // Wait a bit or let user check manually
        // We could poll here, but simplest is to just let user return
    } catch (err) {
        alert("Error creating payment: " + err.message);
    } finally {
        setLoading(false);
    }
}

async function loadConfigs() {
    const list = document.getElementById('configs-list');
    list.innerHTML = '<p class="text-center text-gray-500">Loading...</p>';

    const user = app.currentUser;
    try {
        const configs = await user.functions.getConfigs();

        if (!configs || configs.length === 0) {
            list.innerHTML = '<p class="text-center text-gray-500">No configs found. Buy a subscription to get one.</p>';
            return;
        }

        list.innerHTML = '';
        configs.forEach((conf, index) => {
            const div = document.createElement('div');
            div.className = 'bg-gray-800 rounded-xl p-4 border border-gray-700 fade-in';
            div.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <div>
                        <h4 class="font-bold">${conf.config_name || 'Config #' + (index + 1)}</h4>
                        <p class="text-xs text-gray-400">Expires in: ${conf.period}</p>
                    </div>
                    <button onclick="copyLink('${conf.config_link}')" class="text-blue-400 text-sm hover:underline">Copy Link</button>
                </div>
                <div class="bg-gray-900 p-2 rounded text-xs text-gray-300 break-all font-mono">
                    ${(conf.config_link || '').substring(0, 50)}...
                </div>
            `;
            list.appendChild(div);
        });
    } catch (err) {
        console.error(err);
        list.innerHTML = '<p class="text-center text-red-500">Error loading configs.</p>';
    }
}

window.copyLink = function(link) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(link).then(() => {
            alert("Copied to clipboard!");
        }).catch(err => {
            console.error("Copy failed", err);
            prompt("Copy this link:", link);
        });
    } else {
         prompt("Copy this link:", link);
    }
}

// Start
init();
