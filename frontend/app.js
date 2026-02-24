// Replace with your actual Realm App ID
const REALM_APP_ID = "application-0-xxxxx";

const app = new Realm.App({ id: REALM_APP_ID });
let currentUser = null;

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Main Logic
async function init() {
    try {
        const initData = tg.initData;
        if (!initData) {
            // Fallback for development outside Telegram (optional)
            console.warn("No initData found. Run inside Telegram.");
            // document.getElementById('loading').innerText = "Please open in Telegram";
            // return;
        }

        // Authenticate with Realm using Custom Function Auth
        const credentials = Realm.Credentials.function({ initData: initData });
        currentUser = await app.logIn(credentials);

        console.log("Logged in as:", currentUser.id);

        // Load initial data
        await loadProfile();

        // Hide loading, show app
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('app').classList.remove('hidden');
        document.getElementById('app').classList.add('fade-in');

    } catch (err) {
        console.error("Failed to login:", err);
        document.getElementById('loading').innerHTML = `<p class="text-red-500 p-4">Login Failed. Please restart.</p>`;
    }
}

// Navigation
function showSection(sectionId) {
    // Hide all sections
    ['profile-section', 'shop-section', 'configs-section', 'topup-section'].forEach(id => {
        document.getElementById(id).classList.add('hidden');
    });

    // Show target
    document.getElementById(sectionId).classList.remove('hidden');
    document.getElementById(sectionId).classList.add('fade-in');

    // Update Bottom Nav
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active', 'text-blue-400', 'text-gray-400'));

    // Highlight active nav item
    if (sectionId === 'profile-section') {
        document.querySelector('button[onclick="showSection(\'profile-section\')"]').classList.add('active', 'text-blue-400');
        loadProfile(); // Refresh profile
    } else if (sectionId === 'shop-section') {
        document.querySelector('button[onclick="showSection(\'shop-section\')"]').classList.add('active', 'text-blue-400');
    } else if (sectionId === 'configs-section') {
        document.querySelector('button[onclick="showSection(\'configs-section\')"]').classList.add('active', 'text-blue-400');
        loadConfigs();
    }
}

// Data Fetching
async function loadProfile() {
    if (!currentUser) return;
    try {
        const profile = await currentUser.functions.getProfile();

        document.getElementById('username').innerText = '@' + (profile.username || 'user');
        document.getElementById('balance').innerText = profile.balance.toFixed(2);
        document.getElementById('referrals-count').innerText = profile.referrals_count;

        const subEnd = profile.subscription_end;
        const statusEl = document.getElementById('subscription-status');

        if (subEnd && new Date(subEnd) > new Date()) {
            const daysLeft = Math.ceil((new Date(subEnd) - new Date()) / (1000 * 60 * 60 * 24));
            statusEl.innerHTML = `<span class="text-green-400 font-bold">Active</span> (${daysLeft} days left)<br><span class="text-xs text-gray-500">Expires: ${new Date(subEnd).toLocaleDateString()}</span>`;
        } else {
            statusEl.innerHTML = `<span class="text-red-400 font-bold">Inactive</span> <br><button onclick="showSection('shop-section')" class="text-blue-400 text-sm underline">Buy Subscription</button>`;
        }

    } catch (err) {
        console.error("Error loading profile:", err);
        tg.showAlert("Failed to load profile.");
    }
}

async function loadConfigs() {
    if (!currentUser) return;
    const listEl = document.getElementById('configs-list');
    listEl.innerHTML = '<p class="text-gray-400 text-center">Loading...</p>';

    try {
        const configs = await currentUser.functions.getConfigs();

        if (!configs || configs.length === 0) {
            listEl.innerHTML = '<p class="text-gray-400 text-center">No configs yet.</p><button onclick="showSection(\'shop-section\')" class="block mx-auto mt-4 text-blue-400 underline">Buy one now</button>';
            return;
        }

        listEl.innerHTML = configs.map(conf => `
            <div class="bg-gray-800 p-3 rounded border border-gray-700">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-sm">${conf.config_name}</h3>
                    <span class="text-xs text-gray-500">${new Date(conf.issue_date).toLocaleDateString()}</span>
                </div>
                <div class="bg-gray-900 p-2 rounded text-xs font-mono text-gray-300 break-all mb-2 select-all">
                    ${conf.config_link || conf.config_code}
                </div>
                <button onclick="copyToClipboard('${conf.config_link || conf.config_code}')" class="w-full bg-blue-900 hover:bg-blue-800 text-blue-200 py-1 rounded text-xs">
                    Copy Link
                </button>
            </div>
        `).join('');

    } catch (err) {
        console.error("Error loading configs:", err);
        listEl.innerHTML = '<p class="text-red-400 text-center">Failed to load configs.</p>';
    }
}

// Actions
async function buySubscription(period) {
    if (!currentUser) return;

    // Confirm dialog
    const confirm = await new Promise(resolve => {
        tg.showPopup({
            title: 'Confirm Purchase',
            message: `Buy ${period.replace('_', ' ')} subscription?`,
            buttons: [
                {id: 'ok', type: 'ok', text: 'Buy'},
                {id: 'cancel', type: 'cancel'}
            ]
        }, (btn) => resolve(btn === 'ok'));
    });

    if (!confirm) return;

    tg.MainButton.showProgress();

    try {
        const result = await currentUser.functions.buySubscription(period);
        tg.MainButton.hideProgress();

        if (result.success) {
            tg.showAlert("Purchase Successful!");
            showSection('profile-section');
        }
    } catch (err) {
        tg.MainButton.hideProgress();
        console.error("Purchase failed:", err);
        tg.showAlert(`Error: ${err.message || "Purchase failed"}`);
    }
}

function setTopUpAmount(amount) {
    document.getElementById('topup-amount').value = amount;
}

async function processTopUp() {
    if (!currentUser) return;
    const amount = parseFloat(document.getElementById('topup-amount').value);

    if (!amount || amount < 50) {
        tg.showAlert("Minimum top up is 50 RUB");
        return;
    }

    tg.MainButton.setText(`Pay ${amount} RUB`);
    tg.MainButton.show();
    tg.MainButton.showProgress();

    try {
        const result = await currentUser.functions.createPayment(amount);
        tg.MainButton.hideProgress();
        tg.MainButton.hide();

        if (result && result.confirmation_url) {
            tg.openLink(result.confirmation_url);

            // Poll for payment status? Or just let user refresh manually.
            // For better UX, we could poll checkPayment here for a few seconds.
            // But usually user comes back and we refresh profile.
        } else {
            tg.showAlert("Failed to create payment link.");
        }
    } catch (err) {
        tg.MainButton.hideProgress();
        tg.MainButton.hide();
        console.error("Topup failed:", err);
        tg.showAlert("Error creating payment.");
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        tg.showPopup({ message: "Copied to clipboard!" });
    });
}

// Copy Referral Link
document.getElementById('copy-referral').addEventListener('click', () => {
    if (!currentUser) return;
    const refLink = `https://t.me/vpni50_bot?start=${currentUser.id}`;
    copyToClipboard(refLink);
});

// Start
init();
