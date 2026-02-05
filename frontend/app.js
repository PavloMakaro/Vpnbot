// Initialize Realm
// REPLACE WITH YOUR REALM APP ID
const APP_ID = "vpn-bot-app-id";
const app = new Realm.App({ id: APP_ID });

let currentUser = null;
let userProfile = null;

// Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

async function init() {
    try {
        if (!tg.initData) {
            throw new Error("Please open from Telegram");
        }

        // Login
        const credentials = Realm.Credentials.customFunction({ initData: tg.initData });
        currentUser = await app.logIn(credentials);
        console.log("Logged in:", currentUser.id);

        // Fetch Data
        await refreshData();

        // Render Plans
        await renderPlans();

        // Show UI
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('main').classList.remove('hidden');
        showView('shop');

    } catch (e) {
        console.error(e);
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('error').classList.remove('hidden');
        document.getElementById('error-msg').innerText = e.message;
    }
}

async function refreshData() {
    userProfile = await currentUser.functions.getUserProfile();
    updateHeader();
}

function updateHeader() {
    document.getElementById('user-name').innerText = userProfile.first_name;
    document.getElementById('user-balance').innerText = userProfile.balance;

    const statusEl = document.getElementById('sub-status');
    const daysEl = document.getElementById('days-left');

    if (userProfile.days_left > 0) {
        statusEl.innerText = "Active";
        statusEl.className = "text-xs px-2 py-1 rounded bg-green-600";
        daysEl.innerText = `${userProfile.days_left} days left`;
    } else {
        statusEl.innerText = "Inactive";
        statusEl.className = "text-xs px-2 py-1 rounded bg-red-600";
        daysEl.innerText = "Expired";
    }
}

async function renderPlans() {
    const plans = await currentUser.functions.getAvailablePlans();
    const container = document.getElementById('plans-container');
    container.innerHTML = '';

    for (const [key, plan] of Object.entries(plans)) {
        const el = document.createElement('div');
        el.className = "bg-gray-800 p-4 rounded-lg flex justify-between items-center";
        el.innerHTML = `
            <div>
                <h3 class="font-bold">${plan.name}</h3>
                <p class="text-sm text-gray-400">${plan.days} days</p>
            </div>
            <button onclick="buySubscription('${key}', ${plan.price})" class="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded text-sm font-bold">
                ${plan.price} ₽
            </button>
        `;
        container.appendChild(el);
    }
}

async function buySubscription(periodKey, price) {
    if (userProfile.balance < price) {
        tg.showAlert("Insufficient balance. Please top up.");
        showView('topup');
        return;
    }

    tg.showConfirm(`Buy ${periodKey} subscription for ${price} ₽?`, async (confirmed) => {
        if (confirmed) {
            try {
                tg.MainButton.showProgress();
                const result = await currentUser.functions.buySubscription(periodKey);
                tg.MainButton.hideProgress();

                if (result.success) {
                    tg.showAlert("Success! Config assigned.");
                    await refreshData();
                    showView('configs');
                }
            } catch (e) {
                tg.MainButton.hideProgress();
                tg.showAlert("Error: " + e.message);
            }
        }
    });
}

async function renderConfigs() {
    const configs = await currentUser.functions.getMyConfigs();
    const container = document.getElementById('configs-container');
    container.innerHTML = '';

    if (configs.length === 0) {
        container.innerHTML = '<p class="text-gray-400 text-center">No configs yet.</p>';
        return;
    }

    configs.forEach(conf => {
        const el = document.createElement('div');
        el.className = "bg-gray-800 p-4 rounded-lg overflow-hidden";
        el.innerHTML = `
            <div class="flex justify-between mb-2">
                <span class="font-bold text-sm">${conf.config_name || 'Config'}</span>
                <span class="text-xs text-gray-400">${conf.period}</span>
            </div>
            <div class="bg-gray-900 p-2 rounded text-xs text-gray-300 break-all cursor-pointer hover:text-white" onclick="copyToClipboard('${conf.config_link}')">
                ${conf.config_link.substring(0, 40)}...
            </div>
            <p class="text-xs text-gray-500 mt-1">Tap link to copy</p>
        `;
        container.appendChild(el);
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        tg.showAlert("Link copied to clipboard!");
    });
}

async function initTopup(amount) {
    try {
        tg.MainButton.showProgress();
        const url = await currentUser.functions.createPayment(amount);
        tg.MainButton.hideProgress();
        tg.openLink(url);
    } catch (e) {
        tg.MainButton.hideProgress();
        tg.showAlert("Error: " + e.message);
    }
}

function initCustomTopup() {
    const amount = parseFloat(document.getElementById('custom-amount').value);
    if (!amount || amount < 50) {
        tg.showAlert("Minimum amount is 50 ₽");
        return;
    }
    initTopup(amount);
}

function showView(viewName) {
    document.querySelectorAll('.view').forEach(el => el.classList.add('hidden'));
    document.getElementById(`view-${viewName}`).classList.remove('hidden');

    if (viewName === 'configs') {
        renderConfigs();
    }
}

// Start
init();
