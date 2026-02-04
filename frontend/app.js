// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();
tg.enableClosingConfirmation();

// Set theme colors
document.documentElement.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#111827');
document.documentElement.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#ffffff');
document.documentElement.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#2563eb');
document.documentElement.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');

// === MONGODB APP SERVICES (STITCH) CONFIG ===
const APP_ID = 'vpn-bot-xxxxx'; // REPLACE WITH YOUR REALM APP ID
let appClient = null;

try {
    if (window.Realm && APP_ID !== 'vpn-bot-xxxxx') {
        appClient = new Realm.App({ id: APP_ID });
    }
} catch (e) {
    console.warn("Failed to init Realm:", e);
}

// Mock Data & State (Fallback)
let userState = {
    balance: 0,
    subscription_end: null,
    configs: [],
    referralLink: ''
};

const PLANS = {
    '1_month': { id: '1_month', price: 50, days: 30, name: '1 Month', badge: '' },
    '2_months': { id: '2_months', price: 90, days: 60, name: '2 Months', badge: '-10%' },
    '3_months': { id: '3_months', price: 120, days: 90, name: '3 Months', badge: 'Best Value' }
};

// API Client
const api = {
    async login() {
        if (!appClient) return null;
        if (appClient.currentUser) return appClient.currentUser;

        // In production, use Custom JWT Auth with Telegram InitData
        // const credentials = Realm.Credentials.jwt(tg.initData);
        // For testing/demo: Anonymous
        const credentials = Realm.Credentials.anonymous();
        return await appClient.logIn(credentials);
    },

    async getUser() {
        if (appClient) {
            try {
                const user = await this.login();
                // Call the 'getUser' function defined in Stitch
                // We pass initData in custom_data or as argument if using JWT
                return await user.functions.getUser();
            } catch (e) {
                console.warn("Stitch call failed, falling back to mock", e);
            }
        }

        // Mock return
        await new Promise(r => setTimeout(r, 500));
        return {
            balance: userState.balance,
            subscription_end: userState.subscription_end,
            referrals_count: 0,
            username: tg.initDataUnsafe.user?.username || 'Guest',
            id: tg.initDataUnsafe.user?.id || 12345
        };
    },

    async getConfigs() {
        if (appClient) {
            try {
                const user = await this.login();
                return await user.functions.getConfigs();
            } catch (e) { console.warn(e); }
        }

        await new Promise(r => setTimeout(r, 400));
        return userState.configs;
    },

    async buySubscription(planId) {
        if (appClient) {
            try {
                const user = await this.login();
                const result = await user.functions.buySubscription(planId);
                return result;
            } catch (e) {
                console.warn(e);
                throw new Error(e.error || "Purchase failed");
            }
        }

        await new Promise(r => setTimeout(r, 800));
        const plan = PLANS[planId];

        if (userState.balance < plan.price) {
            throw new Error("Insufficient balance");
        }

        userState.balance -= plan.price;

        const currentEnd = userState.subscription_end ? new Date(userState.subscription_end) : new Date();
        if (currentEnd < new Date()) {
            currentEnd.setTime(Date.now());
        }

        currentEnd.setDate(currentEnd.getDate() + plan.days);
        userState.subscription_end = currentEnd.toISOString();

        const newConfig = {
            id: Date.now(),
            name: `${plan.name} Config`,
            link: `vless://mock-config-${Date.now()}@vpn.server.com:443`,
            period: planId,
            date: new Date().toISOString().split('T')[0]
        };
        userState.configs.push(newConfig);

        return { success: true, new_end: userState.subscription_end, config: newConfig };
    },

    async topUp(amount) {
        // Payment usually happens via external link, logic is same for both
        await new Promise(r => setTimeout(r, 600));
        return { success: true, payment_url: `https://yookassa.ru/checkout/mock/${Date.now()}?amount=${amount}` };
    }
};

// UI Logic
function navTo(viewId) {
    document.querySelectorAll('.view').forEach(el => el.classList.add('hidden'));
    const target = document.getElementById(`view-${viewId}`);
    if (target) target.classList.remove('hidden');

    document.querySelectorAll('.nav-btn').forEach(btn => {
        if (btn.dataset.target === viewId) {
            btn.classList.add('active', 'text-blue-500');
            btn.classList.remove('text-gray-500');
        } else {
            btn.classList.remove('active', 'text-blue-500');
            btn.classList.add('text-gray-500');
        }
    });

    if (viewId === 'dashboard') loadDashboard();
    if (viewId === 'shop') loadShop();
    if (viewId === 'configs') loadConfigs();

    if (viewId === 'topup') {
        tg.MainButton.text = "PAY";
        tg.MainButton.hide();
    } else {
        tg.MainButton.hide();
    }
}

async function loadDashboard() {
    try {
        const user = await api.getUser();

        // Update local state if we got data from real backend
        if (appClient) {
             userState.balance = user.balance;
             userState.subscription_end = user.subscription_end;
        }

        document.getElementById('user-balance').innerText = user.balance;

        const badge = document.getElementById('status-badge');
        const subInfo = document.getElementById('sub-info');

        if (user.subscription_end && new Date(user.subscription_end) > new Date()) {
            const endDate = new Date(user.subscription_end);
            const daysLeft = Math.ceil((endDate - new Date()) / (1000 * 60 * 60 * 24));

            badge.innerText = 'Active';
            badge.className = 'bg-green-600/20 text-green-400 text-xs px-2 py-1 rounded-full';
            subInfo.innerText = `Active for ${daysLeft} days (until ${endDate.toLocaleDateString()})`;
        } else {
            badge.innerText = 'Inactive';
            badge.className = 'bg-red-600/20 text-red-400 text-xs px-2 py-1 rounded-full';
            subInfo.innerText = 'No active subscription';
        }

        const botUsername = "vpni50_bot";
        const refLink = `https://t.me/${botUsername}?start=${user.id || user._id}`;
        document.getElementById('ref-link').innerText = refLink;
        document.getElementById('ref-count').innerText = user.referrals_count || 0;
        userState.referralLink = refLink;

    } catch (e) {
        console.error(e);
        tg.showAlert("Failed to load user data");
    }
}

function loadShop() {
    const container = document.getElementById('plans-container');
    container.innerHTML = '';

    Object.values(PLANS).forEach(plan => {
        const el = document.createElement('div');
        el.className = 'bg-gray-800 rounded-xl p-4 border border-gray-700 relative overflow-hidden active:scale-[0.98] transition cursor-pointer';
        el.onclick = () => confirmPurchase(plan.id);

        let badgeHtml = '';
        if (plan.badge) {
            badgeHtml = `<div class="absolute top-0 right-0 bg-blue-600 text-white text-[10px] px-2 py-1 rounded-bl-lg font-bold">${plan.badge}</div>`;
        }

        el.innerHTML = `
            ${badgeHtml}
            <div class="flex justify-between items-center">
                <div>
                    <div class="text-lg font-bold text-white">${plan.name}</div>
                    <div class="text-sm text-gray-400">${plan.days} days access</div>
                </div>
                <div class="text-right">
                    <div class="text-xl font-bold text-blue-400">${plan.price} ₽</div>
                </div>
            </div>
        `;
        container.appendChild(el);
    });
}

function confirmPurchase(planId) {
    const plan = PLANS[planId];
    if (userState.balance < plan.price) {
        tg.showPopup({
            title: 'Insufficient Balance',
            message: `You need ${plan.price - userState.balance} ₽ more. Top up now?`,
            buttons: [{id: 'topup', type: 'default', text: 'Top Up'}, {type: 'cancel'}]
        }, (btnId) => {
            if (btnId === 'topup') navTo('topup');
        });
        return;
    }

    tg.showConfirm(`Buy ${plan.name} for ${plan.price} ₽?`, async (confirm) => {
        if (confirm) {
            try {
                tg.MainButton.showProgress();
                const result = await api.buySubscription(planId);
                tg.MainButton.hideProgress();
                tg.MainButton.hide();

                tg.showAlert("Successfully purchased! Config is ready.", () => {
                    navTo('configs');
                });
            } catch (e) {
                tg.MainButton.hideProgress();
                tg.showAlert(e.message);
            }
        }
    });
}

async function loadConfigs() {
    const container = document.getElementById('configs-container');
    container.innerHTML = '<div class="text-center text-gray-500 py-4">Loading...</div>';

    const configs = await api.getConfigs();
    container.innerHTML = '';

    if (!configs || configs.length === 0) {
        container.innerHTML = `
            <div class="text-center py-10">
                <div class="text-gray-500 mb-4 text-4xl"><i class="fas fa-box-open"></i></div>
                <p class="text-gray-400 mb-4">No configs found.</p>
                <button onclick="navTo('shop')" class="bg-blue-600 px-6 py-2 rounded-full text-sm font-bold">Buy Subscription</button>
            </div>
        `;
        return;
    }

    configs.forEach(conf => {
        const el = document.createElement('div');
        el.className = 'bg-gray-800 rounded-xl p-4 border border-gray-700 mb-3';
        const date = conf.date || conf.issue_date || 'N/A';
        const link = conf.link || conf.config_link || '';
        const name = conf.name || conf.config_name || 'Config';

        el.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <div>
                    <div class="font-bold text-white">${name}</div>
                    <div class="text-xs text-gray-400">${date}</div>
                </div>
                <div class="bg-green-900/50 text-green-400 text-xs px-2 py-1 rounded">Active</div>
            </div>
            <div class="bg-gray-900 p-2 rounded text-xs font-mono text-gray-400 break-all mb-3 select-all">
                ${link.substring(0, 30)}...
            </div>
            <div class="flex gap-2">
                <button onclick="copyToClipboard('${link}')" class="flex-1 bg-gray-700 hover:bg-gray-600 py-2 rounded-lg text-xs font-medium">Copy</button>
                <button onclick="showInstructions()" class="flex-1 bg-gray-700 hover:bg-gray-600 py-2 rounded-lg text-xs font-medium">How to use</button>
            </div>
        `;
        container.appendChild(el);
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        tg.showPopup({message: 'Copied to clipboard!'});
    });
}

function showInstructions() {
    tg.openLink('https://telegra.ph/VPN-Instructions-01-01');
}

function selectAmount(amount) {
    document.getElementById('custom-amount').value = amount;
}

function initiateTopUp() {
    const amount = document.getElementById('custom-amount').value;
    if (!amount || amount < 10) {
        tg.showAlert("Minimum amount is 10 ₽");
        return;
    }

    tg.showConfirm(`Top up ${amount} ₽?`, async (confirm) => {
        if (confirm) {
            tg.openLink(`https://yookassa.ru/integration/simplepay/payment?amount=${amount}`);
            // Mock simulation
             setTimeout(() => {
                 userState.balance += parseInt(amount);
                 tg.showAlert(`Mock Payment Success! Added ${amount} ₽`, () => {
                     navTo('dashboard');
                 });
             }, 2000);
        }
    });
}

function copyRefLink() {
    copyToClipboard(userState.referralLink);
}

// Init
window.addEventListener('load', () => {
    navTo('dashboard');
});
