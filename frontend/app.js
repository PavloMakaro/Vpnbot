const REALM_APP_ID = "vpn-bot-xxxxx"; // REPLACE WITH YOUR REALM APP ID

const tg = window.Telegram.WebApp;
tg.expand();

const realmApp = new Realm.App({ id: REALM_APP_ID });
let currentUser = null;
let userProfile = null;

const router = {
    navigate: (viewId) => {
        document.querySelectorAll('[id$="-view"]').forEach(el => el.classList.add('hidden'));
        document.getElementById('loading').classList.add('hidden');
        document.getElementById(`${viewId}-view`).classList.remove('hidden');

        if (viewId === 'home') app.renderHome();
        if (viewId === 'shop') app.renderShop();
        if (viewId === 'configs') app.renderConfigs();
        if (viewId === 'referral') app.renderReferral();

        tg.BackButton.isVisible = viewId !== 'home';
        tg.BackButton.onClick(() => router.navigate('home'));
    }
};

const app = {
    init: async () => {
        try {
            // Auth with Telegram initData
            const initData = tg.initData;
            if (!initData) {
                alert("Please open this app from Telegram.");
                return;
            }

            const credentials = Realm.Credentials.customFunction(initData);
            currentUser = await realmApp.logIn(credentials);
            console.log("Logged in as", currentUser.id);

            await app.fetchProfile();
            router.navigate('home');
        } catch (err) {
            console.error("Login failed", err);
            alert("Login failed: " + err.message);
        }
    },

    fetchProfile: async () => {
        userProfile = await currentUser.functions.getUserProfile();
    },

    renderHome: () => {
        if (!userProfile) return;
        document.getElementById('username').innerText = '@' + (userProfile.username || 'user');
        document.getElementById('balance').innerText = userProfile.balance;

        const subStatusEl = document.getElementById('sub-status');
        if (userProfile.days_left > 0) {
            subStatusEl.innerText = `Active (${userProfile.days_left} days left)`;
            subStatusEl.className = "font-semibold text-green-600";
        } else {
            subStatusEl.innerText = "Inactive";
            subStatusEl.className = "font-semibold text-red-500";
        }
    },

    renderShop: async () => {
        const list = document.getElementById('products-list');
        list.innerHTML = '<div class="text-center">Loading plans...</div>';

        try {
            const plans = await currentUser.functions.getConfigs(); // This returns the pricing object
            list.innerHTML = '';

            Object.entries(plans).forEach(([key, plan]) => {
                const item = document.createElement('div');
                item.className = 'card p-4 rounded-lg shadow flex justify-between items-center';
                item.innerHTML = `
                    <div>
                        <div class="font-bold">${plan.days} Days</div>
                        <div class="text-sm text-gray-600">${plan.price} RUB</div>
                    </div>
                    <button class="btn-primary px-4 py-2 rounded text-sm font-bold" onclick="app.buy('${key}')">Buy</button>
                `;
                list.appendChild(item);
            });
        } catch (err) {
            list.innerHTML = '<div class="text-red-500">Error loading plans</div>';
        }
    },

    topUp: async () => {
        const amount = document.getElementById('topup-amount').value;
        if (!amount || amount < 50) {
            alert("Minimum amount is 50 RUB");
            return;
        }

        try {
            tg.MainButton.showProgress();
            const result = await currentUser.functions.createPayment(amount);
            if (result && result.confirmation_url) {
                tg.openLink(result.confirmation_url);
            }
        } catch (err) {
            alert("Payment creation failed: " + err.message);
        } finally {
            tg.MainButton.hideProgress();
        }
    },

    buy: async (periodKey) => {
        if (!confirm("Are you sure you want to buy this plan?")) return;

        try {
            tg.MainButton.showProgress();
            const result = await currentUser.functions.buySubscription(periodKey);
            if (result.success) {
                alert("Successfully purchased!");
                await app.fetchProfile();
                router.navigate('configs'); // Go to configs to see the new one
            }
        } catch (err) {
            alert("Purchase failed: " + err.message);
        } finally {
            tg.MainButton.hideProgress();
        }
    },

    renderConfigs: () => {
        const list = document.getElementById('configs-list');
        if (!userProfile || !userProfile.used_configs || userProfile.used_configs.length === 0) {
            list.innerHTML = '<div class="text-center text-gray-500">No configs found. Buy a subscription first!</div>';
            return;
        }

        list.innerHTML = '';
        // Sort by date desc
        const sorted = [...userProfile.used_configs].reverse();

        sorted.forEach(conf => {
            const item = document.createElement('div');
            item.className = 'card p-4 rounded-lg shadow space-y-2';
            const date = new Date(conf.issue_date).toLocaleDateString();
            item.innerHTML = `
                <div class="flex justify-between font-bold">
                    <span>${conf.config_name || 'VPN Config'}</span>
                    <span class="text-xs font-normal text-gray-500">${date}</span>
                </div>
                <div class="text-xs bg-gray-200 p-2 rounded break-all font-mono select-all">
                    ${conf.config_link.substring(0, 30)}...
                </div>
                <button class="w-full btn-primary py-2 rounded text-sm" onclick="navigator.clipboard.writeText('${conf.config_link}').then(() => alert('Copied!'))">
                    Copy Link
                </button>
            `;
            list.appendChild(item);
        });
    },

    renderReferral: () => {
        const refLink = `https://t.me/vpni50_bot?start=${currentUser.id}`; // Assuming bot username
        document.getElementById('ref-link-container').innerText = refLink;
        document.getElementById('ref-count').innerText = userProfile.referrals_count || 0;

        document.getElementById('ref-link-container').onclick = () => {
             navigator.clipboard.writeText(refLink).then(() => alert('Copied!'));
        };
    }
};

// Start app
app.init();
