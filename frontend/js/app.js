// Constants
const REALM_APP_ID = "vpn-bot-app-id"; // REPLACE WITH YOUR REALM APP ID

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Initialize Realm
const app = new Realm.App({ id: REALM_APP_ID });

// State
let currentUser = null;
let userProfile = null;

// DOM Elements
const loader = document.getElementById('loader');

// Navigation
function navTo(sectionId) {
    document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
    document.getElementById(`${sectionId}-section`).classList.add('active');

    if (sectionId === 'plans') loadPlans();
    if (sectionId === 'home') loadUserData();
    if (sectionId === 'profile') loadProfile();

    tg.BackButton.isVisible = sectionId !== 'home';
    if (sectionId !== 'home') {
        tg.BackButton.onClick(() => navTo('home'));
    } else {
        tg.BackButton.offClick();
    }
}

// Authentication
async function initApp() {
    try {
        const initData = tg.initData;
        if (!initData) {
            console.warn("No initData found. Running in demo/dev mode?");
            // For dev testing outside Telegram, you might need a fallback or mock
        }

        // Login to Realm using Custom Function Auth
        const credentials = Realm.Credentials.function({ initData: initData });
        currentUser = await app.logIn(credentials);

        console.log("Logged in as:", currentUser.id);

        await loadUserData();
        loader.classList.add('hidden');

    } catch (err) {
        console.error("Auth Failed:", err);
        alert("Authentication failed. Please restart the bot.");
    }
}

// Data Loading
async function loadUserData() {
    try {
        userProfile = await currentUser.functions.getUser();

        // Update Balance
        document.getElementById('balance-display').textContent = userProfile.balance;

        // Update Subscription
        const subStatus = document.getElementById('subscription-status');
        const subEnd = document.getElementById('subscription-end');

        if (userProfile.days_left > 0) {
            subStatus.textContent = `Active (${userProfile.days_left} days left)`;
            subStatus.classList.add('text-green-600', 'font-bold');
            subEnd.classList.remove('hidden');
            subEnd.querySelector('span').textContent = new Date(userProfile.subscription_end).toLocaleDateString();
        } else {
            subStatus.textContent = "No active subscription";
            subStatus.classList.remove('text-green-600', 'font-bold');
            subEnd.classList.add('hidden');
        }

        // Update Configs List
        const configsList = document.getElementById('configs-list');
        configsList.innerHTML = '';
        if (userProfile.used_configs && userProfile.used_configs.length > 0) {
            userProfile.used_configs.forEach(conf => {
                const div = document.createElement('div');
                div.className = "bg-white p-3 rounded border dark:bg-gray-700 dark:border-gray-600";
                div.innerHTML = `
                    <div class="flex justify-between items-center mb-1">
                        <span class="font-medium">${conf.name}</span>
                        <span class="text-xs text-gray-500">${new Date(conf.issued_at).toLocaleDateString()}</span>
                    </div>
                    <div class="text-xs break-all bg-gray-100 p-2 rounded dark:bg-gray-800 font-mono select-all">
                        ${conf.link}
                    </div>
                `;
                configsList.appendChild(div);
            });
        } else {
             configsList.innerHTML = '<p class="text-gray-500">No configs yet.</p>';
        }

    } catch (err) {
        console.error("Error loading user data:", err);
    }
}

async function loadPlans() {
    const container = document.getElementById('plans-container');
    container.innerHTML = '<div class="text-center">Loading plans...</div>';

    try {
        const plans = await currentUser.functions.getPlans();
        container.innerHTML = '';

        Object.keys(plans).forEach(key => {
            const plan = plans[key];
            const div = document.createElement('div');
            div.className = "bg-white border rounded-xl p-4 flex justify-between items-center shadow-sm dark:bg-gray-800 dark:border-gray-700";
            div.innerHTML = `
                <div>
                    <h3 class="font-bold text-lg">${plan.name}</h3>
                    <p class="text-gray-500 text-sm">${plan.days} days</p>
                </div>
                <div class="text-right">
                    <p class="font-bold text-xl mb-1">${plan.price} ₽</p>
                    <button onclick="buySubscription('${key}')" class="bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-600 transition">
                        Buy
                    </button>
                </div>
            `;
            container.appendChild(div);
        });

    } catch (err) {
        console.error("Error loading plans:", err);
        container.innerHTML = '<div class="text-red-500">Failed to load plans.</div>';
    }
}

function loadProfile() {
    if (userProfile) {
        document.getElementById('profile-id').textContent = userProfile._id;
        document.getElementById('profile-referrals').textContent = userProfile.referrals_count;
    }
}

// Actions
function setAmount(val) {
    document.getElementById('amount-input').value = val;
}

async function initiatePayment() {
    const amount = parseFloat(document.getElementById('amount-input').value);
    if (!amount || amount < 50) {
        tg.showAlert("Minimum amount is 50 ₽");
        return;
    }

    tg.MainButton.showProgress();

    try {
        const result = await currentUser.functions.createPayment(amount);
        tg.MainButton.hideProgress();

        if (result.confirmation_url) {
             tg.openLink(result.confirmation_url);
             // Optionally close webapp or wait
             tg.close();
        } else {
             tg.showAlert("Error creating payment link.");
        }

    } catch (err) {
        tg.MainButton.hideProgress();
        console.error("Payment error:", err);
        tg.showAlert("Payment failed: " + err.message);
    }
}

async function buySubscription(periodKey) {
    if (!confirm("Are you sure you want to buy this subscription?")) return;

    loader.classList.remove('hidden');

    try {
        const result = await currentUser.functions.buySubscription(periodKey);
        loader.classList.add('hidden');

        if (result.success) {
            tg.showAlert("Subscription purchased successfully!");
            navTo('home');
        } else {
            tg.showAlert("Purchase failed.");
        }

    } catch (err) {
        loader.classList.add('hidden');
        console.error("Purchase error:", err);
        tg.showAlert("Purchase failed: " + err.message);
    }
}

// Initialize
window.addEventListener('load', initApp);
window.navTo = navTo;
window.setAmount = setAmount;
window.initiatePayment = initiatePayment;
window.buySubscription = buySubscription;
