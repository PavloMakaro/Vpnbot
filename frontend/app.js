// Constants
const REALM_APP_ID = "vpn-bot-tma-xxxxx"; // TODO: Replace with your actual App ID
const app = new Realm.App({ id: REALM_APP_ID });
const tg = window.Telegram.WebApp;

// State
let currentUser = null;
let userProfile = null;
let pricing = null;

// Router
const router = {
    async navigate(route, params = {}) {
        // Update UI active state
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        const activeNav = document.querySelector(`button[onclick="router.navigate('${route}')"]`);
        if (activeNav) activeNav.classList.add('active');

        // Render
        const container = document.getElementById('app');
        container.innerHTML = '<div class="flex justify-center p-10"><div class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div></div>';

        try {
            switch (route) {
                case 'home':
                    await views.home(container);
                    break;
                case 'shop':
                    await views.shop(container);
                    break;
                case 'profile':
                    await views.profile(container);
                    break;
                case 'topup':
                    await views.topup(container);
                    break;
                default:
                    await views.home(container);
            }
        } catch (e) {
            console.error("Navigation error:", e);
            container.innerHTML = `<div class="text-red-500 text-center mt-10">Error loading page: ${e.message}</div>`;
        }
    }
};

// Views
const views = {
    async home(container) {
        // Refresh profile
        userProfile = await currentUser.functions.getUserProfile();
        const balance = userProfile.balance.toFixed(2);

        let subStatus = '<span class="status-inactive">Inactive</span>';
        let subDate = 'No active subscription';
        if (userProfile.subscription_end) {
            const end = new Date(userProfile.subscription_end);
            if (end > new Date()) {
                subStatus = '<span class="status-active font-bold">Active</span>';
                const daysLeft = Math.ceil((end - new Date()) / (1000 * 60 * 60 * 24));
                subDate = `${daysLeft} days left (until ${end.toLocaleDateString()})`;
            }
        }

        container.innerHTML = `
            <div class="view-animate">
                <div class="flex items-center justify-between mb-6">
                    <div>
                        <h1 class="text-2xl font-bold">Hello, ${userProfile.first_name}</h1>
                        <p class="text-sm text-gray-400">@${userProfile.username}</p>
                    </div>
                    <div class="bg-blue-600 rounded-full h-10 w-10 flex items-center justify-center font-bold text-lg">
                        ${userProfile.first_name.charAt(0)}
                    </div>
                </div>

                <div class="card">
                    <div class="text-sm text-gray-400 mb-1">Your Balance</div>
                    <div class="text-3xl font-bold text-white mb-4">${balance} ₽</div>
                    <button onclick="router.navigate('topup')" class="btn-primary mb-2">Add Funds</button>
                    <button onclick="router.navigate('shop')" class="btn-secondary">Buy Subscription</button>
                </div>

                <div class="card">
                    <div class="text-sm text-gray-400 mb-1">Subscription Status</div>
                    <div class="text-xl mb-1">${subStatus}</div>
                    <div class="text-xs text-gray-500">${subDate}</div>
                </div>

                ${userProfile.referred_by ? `<div class="text-xs text-center text-gray-600 mt-4">Invited by user ID: ${userProfile.referred_by}</div>` : ''}
            </div>
        `;
    },

    async shop(container) {
        if (!pricing) {
            pricing = await currentUser.functions.getConfigs();
        }

        let itemsHtml = '';
        // Sort keys to maintain order 1, 2, 3 months
        const keys = Object.keys(pricing).sort();

        for (const key of keys) {
            const plan = pricing[key];
            const name = plan.name || `${plan.days} Days`;
            itemsHtml += `
                <div class="card flex justify-between items-center">
                    <div>
                        <div class="font-bold text-lg">${name}</div>
                        <div class="text-sm text-gray-400">${plan.price} ₽</div>
                    </div>
                    <button onclick="actions.buy('${key}', '${name}', ${plan.price})" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700">
                        Buy
                    </button>
                </div>
            `;
        }

        container.innerHTML = `
            <div class="view-animate">
                <h2 class="text-xl font-bold mb-4">Select Plan</h2>
                <div class="space-y-4">
                    ${itemsHtml}
                </div>
            </div>
        `;
    },

    async topup(container) {
        container.innerHTML = `
            <div class="view-animate">
                <h2 class="text-xl font-bold mb-4">Add Funds</h2>
                <div class="card">
                    <label class="block text-sm text-gray-400 mb-2">Amount (RUB)</label>
                    <input type="number" id="amountInput" class="w-full bg-gray-700 text-white rounded p-3 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="100" min="50" max="50000">
                    <div class="flex gap-2 mb-4">
                        <button onclick="document.getElementById('amountInput').value=100" class="flex-1 bg-gray-600 py-1 rounded text-xs">100</button>
                        <button onclick="document.getElementById('amountInput').value=300" class="flex-1 bg-gray-600 py-1 rounded text-xs">300</button>
                        <button onclick="document.getElementById('amountInput').value=500" class="flex-1 bg-gray-600 py-1 rounded text-xs">500</button>
                    </div>
                    <button onclick="actions.topup()" class="btn-primary">Pay with YooKassa</button>
                </div>
            </div>
        `;
    },

    async profile(container) {
        // Fetch fresh data
        userProfile = await currentUser.functions.getUserProfile();
        const myConfigs = await currentUser.functions.getMyConfigs();
        const refLink = `https://t.me/${tg.initDataUnsafe?.user?.username || "bot"}?start=${userProfile._id}`; // Simplified link

        let configListHtml = '';
        if (myConfigs && myConfigs.length > 0) {
            configListHtml = myConfigs.map(c => `
                <div class="bg-gray-800 p-3 rounded mb-2 border border-gray-700">
                    <div class="font-bold text-sm text-blue-400 mb-1">${c.name || "Config"} (${c.period})</div>
                    <div class="text-xs text-gray-500 break-all bg-gray-900 p-2 rounded cursor-pointer hover:bg-gray-700 transition" onclick="actions.copy('${c.link}')">
                        ${c.link.substring(0, 30)}... (Tap to Copy)
                    </div>
                    <div class="text-right text-xs text-gray-600 mt-1">${new Date(c.assigned_at).toLocaleDateString()}</div>
                </div>
            `).join('');
        } else {
            configListHtml = '<div class="text-center text-gray-500 py-4">No configs found.</div>';
        }

        container.innerHTML = `
            <div class="view-animate">
                <h2 class="text-xl font-bold mb-4">My Profile</h2>

                <div class="card">
                    <div class="text-sm text-gray-400 mb-2">Referral Program</div>
                    <div class="text-2xl font-bold mb-1">${userProfile.referrals_count} <span class="text-sm font-normal text-gray-500">Invitees</span></div>
                    <div class="mt-2">
                        <div class="text-xs text-gray-400 mb-1">Your Invite Link:</div>
                        <div class="bg-gray-900 p-2 rounded text-xs text-blue-300 break-all cursor-pointer" onclick="actions.copy('${refLink}')">
                            ${refLink}
                        </div>
                    </div>
                </div>

                <h3 class="font-bold text-lg mb-2 mt-6">My Configurations</h3>
                <div class="space-y-2 pb-10">
                    ${configListHtml}
                </div>
            </div>
        `;
    }
};

// Actions
const actions = {
    async topup() {
        const amount = parseFloat(document.getElementById('amountInput').value);
        if (!amount || amount < 50) {
            tg.showAlert("Minimum amount is 50 RUB");
            return;
        }

        try {
            tg.MainButton.showProgress();
            const result = await currentUser.functions.createPayment({
                amount: amount,
                description: `Topup Balance: ${amount} RUB`
            });
            tg.MainButton.hideProgress();

            if (result && result.confirmation && result.confirmation.confirmation_url) {
                tg.openLink(result.confirmation.confirmation_url);
                tg.showPopup({
                    title: "Payment Created",
                    message: "Please complete the payment in the browser. After payment, click Check Status.",
                    buttons: [{id: "check", type: "default", text: "Check Status"}, {type: "cancel"}]
                }, async (btnId) => {
                    if (btnId === "check") {
                        await actions.checkPayment(result.id);
                    }
                });
            }
        } catch (e) {
            tg.MainButton.hideProgress();
            tg.showAlert(`Error: ${e.message}`);
        }
    },

    async checkPayment(paymentId) {
        try {
            const res = await currentUser.functions.checkPayment(paymentId);
            if (res.status === 'succeeded') {
                tg.showAlert("Payment Successful! Balance updated.");
                router.navigate('home');
            } else {
                tg.showAlert(`Payment status: ${res.status}`);
            }
        } catch (e) {
            tg.showAlert(`Error checking status: ${e.message}`);
        }
    },

    async buy(period, name, price) {
        tg.showConfirm(`Buy ${name} for ${price} RUB?`, async (confirm) => {
            if (!confirm) return;

            try {
                tg.MainButton.showProgress();
                const result = await currentUser.functions.buySubscription(period);
                tg.MainButton.hideProgress();

                if (result.success) {
                    tg.showAlert(`Success! Your subscription is active until ${new Date(result.subscription_end).toLocaleDateString()}`);
                    // Navigate to profile to see config
                    router.navigate('profile');
                }
            } catch (e) {
                tg.MainButton.hideProgress();
                tg.showAlert(`Failed: ${e.message}`);
            }
        });
    },

    copy(text) {
        navigator.clipboard.writeText(text).then(() => {
            tg.showAlert("Copied to clipboard!");
        }).catch(err => {
            console.error('Async: Could not copy text: ', err);
            // Fallback
            const textArea = document.createElement("textarea");
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                tg.showAlert("Copied to clipboard!");
            } catch (err) {
                tg.showAlert("Failed to copy");
            }
            document.body.removeChild(textArea);
        });
    }
};

// Initialization
async function init() {
    tg.ready();
    tg.expand();

    // Check initData
    if (!tg.initData) {
        document.getElementById('app').innerHTML = '<div class="text-center mt-10 text-red-500">Please open this app from Telegram.</div>';
        return;
    }

    try {
        // Authenticate
        const credentials = Realm.Credentials.function({ initData: tg.initData });
        currentUser = await app.logIn(credentials);

        // Initial data fetch
        userProfile = await currentUser.functions.getUserProfile({
             start_param: tg.initDataUnsafe?.start_param,
             username: tg.initDataUnsafe?.user?.username,
             first_name: tg.initDataUnsafe?.user?.first_name
        });

        // Setup UI
        document.getElementById('navbar').classList.remove('hidden');
        router.navigate('home');

    } catch (e) {
        console.error("Auth Error:", e);
        document.getElementById('app').innerHTML = `<div class="text-center mt-10 text-red-500">Authentication Failed: ${e.message}</div>`;
    }
}

// Start
init();
