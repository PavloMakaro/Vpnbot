const REALM_APP_ID = "vpn-bot-xxxxx"; // REPLACE WITH YOUR REALM APP ID

const tg = window.Telegram.WebApp;
tg.expand();

// Ensure theme params are applied immediately
document.body.style.backgroundColor = tg.themeParams.bg_color || '#ffffff';
document.body.style.color = tg.themeParams.text_color || '#000000';

const realmApp = new Realm.App({ id: REALM_APP_ID });
let currentUser = null;
let userProfile = null;

const router = {
    history: [],
    navigate: (viewId) => {
        router.history.push(viewId);
        router.updateView(viewId);
    },
    back: () => {
        if (router.history.length > 1) {
            router.history.pop();
            const prevView = router.history[router.history.length - 1];
            router.updateView(prevView);
        } else {
            router.updateView('home'); // Fallback
        }
    },
    updateView: (viewId) => {
        // Hide all views with a quick fade out (optional, simpler to just switch for now)
        document.querySelectorAll('[id$="-view"]').forEach(el => el.classList.add('hidden'));

        const target = document.getElementById(`${viewId}-view`);
        target.classList.remove('hidden');
        // Trigger reflow for animation if needed
        target.classList.remove('fade-in');
        void target.offsetWidth;
        target.classList.add('fade-in');

        if (viewId === 'home') app.renderHome();
        if (viewId === 'shop') app.renderShop();
        if (viewId === 'configs') app.renderConfigs();
        if (viewId === 'referral') app.renderReferral();

        if (viewId === 'home') {
            tg.BackButton.hide();
        } else {
            tg.BackButton.show();
            tg.BackButton.onClick(() => {
                router.back();
                tg.BackButton.offClick(); // Avoid stacking listeners
            });
        }
    }
};

const app = {
    init: async () => {
        try {
            // Simulate minimum loading time for animation effect
            await new Promise(r => setTimeout(r, 800));

            // Auth with Telegram initData
            const initData = tg.initData;
            if (!initData) {
                // For development testing outside TG (remove in production)
                // alert("Please open this app from Telegram.");
                // return;
            }

            // In production, use real credentials
            // const credentials = Realm.Credentials.customFunction(initData);
            // currentUser = await realmApp.logIn(credentials);

            // MOCK LOGIN for Development/Demo purposes (Remove logic if real Auth is ready)
             if (!currentUser && !initData) {
                 // Mock user for UI testing
                 userProfile = { username: "demo_user", balance: 150, days_left: 0, referrals_count: 5, used_configs: [] };
             } else {
                 const credentials = Realm.Credentials.customFunction(initData);
                 currentUser = await realmApp.logIn(credentials);
                 await app.fetchProfile();
             }

            // Show app container
            document.getElementById('loading').classList.add('hidden');
            const container = document.getElementById('app-container');
            container.classList.remove('opacity-0');

            router.navigate('home');
        } catch (err) {
            console.error("Login failed", err);
            document.getElementById('loading').innerHTML = `<div class="text-red-500 p-4 text-center">Login Error: ${err.message}</div>`;
        }
    },

    fetchProfile: async () => {
        if (currentUser) {
            userProfile = await currentUser.functions.getUserProfile();
        }
    },

    renderHome: () => {
        if (!userProfile) return;
        document.getElementById('username').innerText = '@' + (userProfile.username || 'user');

        // Animate balance counter
        const balanceEl = document.getElementById('balance');
        const currentBalance = parseInt(balanceEl.innerText);
        const targetBalance = userProfile.balance;
        if (currentBalance !== targetBalance) {
            balanceEl.innerText = targetBalance; // Simple update, could add counting animation
        }

        const subStatusEl = document.getElementById('sub-status');
        if (userProfile.days_left > 0) {
            subStatusEl.innerText = `Active (${userProfile.days_left} days)`;
            subStatusEl.className = "px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-600";
        } else {
            subStatusEl.innerText = "Inactive";
            subStatusEl.className = "px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-600";
        }
    },

    renderShop: async () => {
        const list = document.getElementById('products-list');
        // Keep skeletons if loading
        // list.innerHTML = '...skeletons...';

        try {
            let plans = {};
            if (currentUser) {
                plans = await currentUser.functions.getConfigs();
            } else {
                // Mock plans
                await new Promise(r => setTimeout(r, 500));
                plans = {
                    '1_month': { days: 30, price: 50 },
                    '3_months': { days: 90, price: 120 }
                };
            }

            list.innerHTML = '';

            Object.entries(plans).forEach(([key, plan]) => {
                const item = document.createElement('div');
                item.className = 'card p-4 rounded-xl shadow-sm flex justify-between items-center transition hover:bg-gray-50';
                item.innerHTML = `
                    <div class="flex flex-col">
                        <span class="font-bold text-lg">${plan.days} Days</span>
                        <span class="text-sm text-[var(--tg-theme-hint-color)]">High speed connection</span>
                    </div>
                    <button class="btn-primary px-5 py-2 rounded-xl text-sm font-bold shadow-md shadow-blue-500/20 active:transform active:scale-95 transition"
                            onclick="app.buy('${key}', ${plan.price})">
                        ${plan.price} ₽
                    </button>
                `;
                list.appendChild(item);
            });
        } catch (err) {
            list.innerHTML = '<div class="text-red-500 text-center">Error loading plans</div>';
        }
    },

    topUp: async () => {
        const amount = document.getElementById('topup-amount').value;
        if (!amount || amount < 50) {
            tg.showAlert("Minimum amount is 50 RUB");
            return;
        }

        try {
            tg.MainButton.text = "Creating Payment...";
            tg.MainButton.showProgress();
            tg.MainButton.show();

            let result = { confirmation_url: "#" };
            if (currentUser) {
                result = await currentUser.functions.createPayment(amount);
            } else {
                 await new Promise(r => setTimeout(r, 1000));
                 tg.showAlert("Mock payment created.");
            }

            if (result && result.confirmation_url) {
                tg.openLink(result.confirmation_url);
            }
        } catch (err) {
            tg.showAlert("Payment failed: " + err.message);
        } finally {
            tg.MainButton.hideProgress();
            tg.MainButton.hide();
        }
    },

    buy: async (periodKey, price) => {
        tg.showConfirm(`Buy subscription for ${price} RUB?`, async (confirmed) => {
            if (!confirmed) return;

            try {
                tg.MainButton.text = "Purchasing...";
                tg.MainButton.showProgress();
                tg.MainButton.show();

                if (currentUser) {
                    const result = await currentUser.functions.buySubscription(periodKey);
                    if (result.success) {
                        tg.showAlert("Successfully purchased!");
                        await app.fetchProfile();
                        router.navigate('configs');
                    }
                } else {
                    // Mock purchase
                    await new Promise(r => setTimeout(r, 1000));
                    tg.showAlert("Mock purchase successful!");
                    // router.navigate('configs');
                }
            } catch (err) {
                tg.showAlert("Purchase failed: " + err.message);
            } finally {
                tg.MainButton.hideProgress();
                tg.MainButton.hide();
            }
        });
    },

    renderConfigs: () => {
        const list = document.getElementById('configs-list');
        if (!userProfile || !userProfile.used_configs || userProfile.used_configs.length === 0) {
            list.innerHTML = `
                <div class="flex flex-col items-center justify-center p-8 text-center opacity-60">
                    <span class="text-4xl mb-2">📂</span>
                    <p>No configs found.</p>
                    <button onclick="router.navigate('shop')" class="mt-4 text-[var(--tg-theme-link-color)]">Get a subscription</button>
                </div>`;
            return;
        }

        list.innerHTML = '';
        const sorted = [...userProfile.used_configs].reverse();

        sorted.forEach(conf => {
            const item = document.createElement('div');
            item.className = 'card p-4 rounded-xl shadow-sm space-y-3';
            const date = new Date(conf.issue_date).toLocaleDateString();
            item.innerHTML = `
                <div class="flex justify-between items-start">
                    <div>
                        <div class="font-bold text-lg">${conf.config_name || 'VPN Config'}</div>
                        <div class="text-xs text-[var(--tg-theme-hint-color)]">${date}</div>
                    </div>
                    <div class="px-2 py-1 bg-green-100 text-green-700 text-xs rounded font-bold">Active</div>
                </div>
                <div class="bg-[var(--tg-theme-bg-color)] p-3 rounded-lg border border-gray-100 font-mono text-xs text-[var(--tg-theme-text-color)] break-all select-all">
                    ${conf.config_link.substring(0, 40)}...
                </div>
                <button class="w-full btn-primary py-3 rounded-xl text-sm font-bold active:scale-95 transition"
                        onclick="navigator.clipboard.writeText('${conf.config_link}').then(() => tg.showAlert('Link Copied!'))">
                    Copy VLESS Key
                </button>
            `;
            list.appendChild(item);
        });
    },

    renderReferral: () => {
        const refLink = `https://t.me/vpni50_bot?start=${currentUser ? currentUser.id : 'user_id'}`;
        const container = document.getElementById('ref-link-container');
        container.innerText = refLink;
        document.getElementById('ref-count').innerText = userProfile ? userProfile.referrals_count : 0;
    },

    copyReferral: () => {
        const link = document.getElementById('ref-link-container').innerText;
        navigator.clipboard.writeText(link).then(() => tg.showAlert('Referral link copied!'));
    }
};

// Start app
app.init();
