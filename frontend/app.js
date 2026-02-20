const APP_ID = "vpn-bot-xyz"; // REPLACE THIS WITH YOUR ATLAS APP ID

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Initialize Realm
const app = new Realm.App({ id: APP_ID });

// State
let currentUser = null;
let userProfile = null;
let availableConfigs = null;

// DOM Elements
const views = {
    home: document.getElementById('view-home'),
    shop: document.getElementById('view-shop'),
    profile: document.getElementById('view-profile'),
    support: document.getElementById('view-support')
};
const appContainer = document.getElementById('app');
const nav = document.getElementById('main-nav');
const loading = document.getElementById('loading');

// Navigation
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        const view = btn.dataset.view;
        switchView(view);

        // Update active state
        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    });
});

async function init() {
    try {
        // Authenticate with Telegram initData
        const initData = tg.initData;
        if (!initData) {
            // Fallback for testing in browser (will fail in real app if strict)
            console.warn("No initData found. Authentication may fail.");
        }

        const credentials = Realm.Credentials.function({ initData: initData });
        currentUser = await app.logIn(credentials);
        console.log("Logged in:", currentUser.id);

        // Check/Init User (handle referrals)
        const startParam = tg.initDataUnsafe.start_param;
        await currentUser.callFunction("login", startParam); // This is the 'initUser' logic

        // Load Data
        await refreshData();

        // Setup UI
        loading.style.display = 'none';
        nav.style.display = 'flex';
        switchView('home');

    } catch (err) {
        console.error("Initialization error:", err);
        appContainer.innerHTML = `<div class="center-screen"><p style="color:red">Error: ${err.message}</p></div>`;
    }
}

async function refreshData() {
    userProfile = await currentUser.callFunction("getUserProfile");
    availableConfigs = await currentUser.callFunction("getConfigs");
}

function switchView(viewName) {
    // Clear container
    appContainer.innerHTML = '';

    switch(viewName) {
        case 'home': renderHome(); break;
        case 'shop': renderShop(); break;
        case 'profile': renderProfile(); break;
        case 'support': renderSupport(); break;
    }
}

// --- VIEWS ---

function renderHome() {
    const balance = userProfile ? userProfile.balance.toFixed(2) : "0.00";
    let subStatus = "No active subscription";
    let subColor = "var(--hint-color)";

    if (userProfile && userProfile.subscription_end) {
        const end = new Date(userProfile.subscription_end);
        if (end > new Date()) {
            const daysLeft = Math.ceil((end - new Date()) / (1000 * 60 * 60 * 24));
            subStatus = `Active (${daysLeft} days left)`;
            subColor = "#34c759"; // Green
        }
    }

    const html = `
        <div class="card text-center">
            <h3>Your Balance</h3>
            <h1 style="font-size: 36px;">${balance} ₽</h1>
            <p class="text-hint">Subscription: <span style="color: ${subColor}">${subStatus}</span></p>

            <div class="input-group mt-4">
                <input type="number" id="amount-input" placeholder="Amount (RUB)" min="50" value="100">
            </div>
            <button class="btn" onclick="handleTopup()">Add Funds</button>
        </div>

        <div class="card" onclick="switchView('shop')">
            <h3>🚀 Buy VPN Subscription</h3>
            <p class="text-hint">Fast, secure, and reliable.</p>
        </div>
    `;
    appContainer.innerHTML = html;
}

function renderShop() {
    let html = `<h1>🛒 Shop</h1>`;

    if (!availableConfigs) {
        html += `<p>Loading plans...</p>`;
    } else {
        html += `<div class="card">`;
        for (const [key, plan] of Object.entries(availableConfigs)) {
            html += `
                <div class="plan-item">
                    <div class="plan-info">
                        <strong>${plan.name || key}</strong>
                        <span class="text-hint">${plan.days} Days</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span class="plan-price">${plan.price} ₽</span>
                        <button class="btn btn-sm" style="padding: 6px 12px;" onclick="handleBuy('${key}', ${plan.price})">Buy</button>
                    </div>
                </div>
            `;
        }
        html += `</div>`;
    }
    appContainer.innerHTML = html;
}

async function renderProfile() {
    appContainer.innerHTML = `<div class="center-screen"><div class="spinner"></div></div>`;

    // Refresh data to get latest configs
    const myConfigs = await currentUser.callFunction("getMyConfigs");

    let html = `<h1>👤 Profile</h1>`;

    // User Info
    html += `
        <div class="card">
            <h3>@${userProfile.username || 'User'}</h3>
            <p>ID: ${userProfile._id}</p>
            <p>Referrals: ${userProfile.referrals_count || 0}</p>
        </div>
    `;

    // Referral
    const refLink = `https://t.me/${tg.initDataUnsafe.bot_username || 'vpn_bot'}?start=${userProfile._id}`;
    html += `
        <div class="card">
            <h3>🤝 Referral Link</h3>
            <div class="input-group">
                <input type="text" value="${refLink}" readonly onclick="this.select()">
            </div>
            <p class="text-hint text-sm">Invite friends and get bonuses!</p>
        </div>
    `;

    // Configs
    html += `<h3>My Configs</h3>`;
    if (myConfigs && myConfigs.length > 0) {
        myConfigs.forEach(conf => {
            const date = new Date(conf.assigned_at || Date.now()).toLocaleDateString();
            html += `
                <div class="card">
                    <div class="plan-item">
                        <div class="plan-info">
                            <strong>${conf.name || 'VPN Config'}</strong>
                            <span class="text-hint">Assigned: ${date}</span>
                        </div>
                    </div>
                    <div class="mt-2">
                        <input type="text" value="${conf.link}" readonly onclick="this.select()" style="font-size: 12px;">
                        <p class="text-hint text-sm mt-2">Click to copy link</p>
                    </div>
                </div>
            `;
        });
    } else {
        html += `<p class="text-hint text-center">No configs found.</p>`;
    }

    appContainer.innerHTML = html;
}

function renderSupport() {
    appContainer.innerHTML = `
        <h1>💬 Support</h1>
        <div class="card text-center">
            <p>Need help?</p>
            <button class="btn" onclick="window.Telegram.WebApp.openTelegramLink('https://t.me/Gl1ch555')">Contact Admin</button>
        </div>
    `;
}

// --- ACTIONS ---

window.handleTopup = async () => {
    const amountInput = document.getElementById('amount-input');
    const amount = parseFloat(amountInput.value);

    if (!amount || amount < 50) {
        tg.showAlert("Minimum amount is 50 RUB");
        return;
    }

    const btn = document.querySelector('button[onclick="handleTopup()"]');
    btn.disabled = true;
    btn.innerText = "Processing...";

    try {
        const result = await currentUser.callFunction("createPayment", amount);
        if (result && result.confirmation_url) {
            tg.openLink(result.confirmation_url);
        } else {
            tg.showAlert("Failed to create payment link.");
        }
    } catch (err) {
        tg.showAlert("Error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerText = "Add Funds";
    }
};

window.handleBuy = async (period, price) => {
    if (userProfile.balance < price) {
        tg.showConfirm("Insufficient funds. Go to home to top up?", (ok) => {
            if (ok) switchView('home');
        });
        return;
    }

    tg.showConfirm(`Buy subscription for ${price} RUB?`, async (ok) => {
        if (!ok) return;

        tg.MainButton.showProgress();
        try {
            const result = await currentUser.callFunction("buySubscription", period);
            await refreshData();
            tg.showAlert("Success! Config assigned.");
            switchView('profile');
        } catch (err) {
            tg.showAlert("Error: " + err.message);
        } finally {
            tg.MainButton.hideProgress();
        }
    });
};

// Start
init();
