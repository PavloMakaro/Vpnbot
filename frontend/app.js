const APP_ID = "application-0-xxxx"; // REPLACE WITH YOUR REALM APP ID

// Initialize Realm App
const realmApp = new Realm.App({ id: APP_ID });

// Global State
const state = {
    user: null,
    profile: null,
    configs: []
};

// Router
const router = {
    history: [],

    navigate: (viewId) => {
        // Hide all views
        document.querySelectorAll('.view').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.view').forEach(el => el.classList.remove('fade-in'));

        // Show target view
        const target = document.getElementById(viewId + '-view');
        if (target) {
            target.classList.remove('hidden');
            target.classList.add('fade-in');
            router.history.push(viewId);
        }

        // Specific view logic
        if (viewId === 'configs') appLogic.loadConfigs();
        if (viewId === 'referral') appLogic.loadReferral();
    },

    back: () => {
        if (router.history.length > 1) {
            router.history.pop(); // Current
            const previous = router.history.pop(); // Previous
            router.navigate(previous);
        } else {
            router.navigate('home');
        }
    }
};

// App Logic
const appLogic = {

    init: async () => {
        try {
            // Telegram WebApp Init
            const tg = window.Telegram.WebApp;
            tg.ready();
            tg.expand();

            // Authentication
            const initData = tg.initData;

            if (!initData) {
                // Fallback for development (remove in production)
                console.warn("No initData found. Running in dev mode?");
                // document.getElementById('loading-view').innerText = "Please open in Telegram";
                // return;
            }

            // Log in using Custom Function Auth
            const credentials = Realm.Credentials.function({ initData: initData });
            state.user = await realmApp.logIn(credentials);
            console.log("Logged in as:", state.user.id);

            // Fetch Profile
            await appLogic.loadProfile();

            // Hide loading, show home
            document.getElementById('loading-view').classList.add('hidden');
            router.navigate('home');

        } catch (err) {
            console.error("Init Error:", err);
            document.getElementById('loading-view').innerHTML = `<p class="text-red-500">Error: ${err.message}</p>`;
        }
    },

    loadProfile: async () => {
        if (!state.user) return;
        try {
            const profile = await state.user.functions.getUserProfile();
            state.profile = profile;

            // Update UI
            document.getElementById('user-name').innerText = profile.first_name || "User";
            document.getElementById('user-username').innerText = profile.username ? `@${profile.username}` : "";
            document.getElementById('user-balance').innerText = `${profile.balance} ₽`;

            // Subscription Status
            const subEnd = profile.subscription_end ? new Date(profile.subscription_end) : null;
            const now = new Date();
            const isActive = subEnd && subEnd > now;

            const badge = document.getElementById('sub-status-badge');
            const details = document.getElementById('sub-details');

            if (isActive) {
                badge.innerText = "Active";
                badge.classList.remove('bg-gray-100', 'text-gray-600');
                badge.classList.add('bg-green-100', 'text-green-600');
                const daysLeft = Math.ceil((subEnd - now) / (1000 * 60 * 60 * 24));
                details.innerText = `Valid until ${subEnd.toLocaleDateString()} (${daysLeft} days left)`;
            } else {
                badge.innerText = "Inactive";
                badge.classList.remove('bg-green-100', 'text-green-600');
                badge.classList.add('bg-gray-100', 'text-gray-600');
                details.innerText = "Purchase a plan to get started.";
            }

        } catch (err) {
            console.error("Load Profile Error:", err);
            appLogic.showToast("Failed to load profile");
        }
    },

    buySubscription: async (planId) => {
        if (!state.user) return;

        // UI Confirmation (Telegram Popup)
        const tg = window.Telegram.WebApp;
        tg.showConfirm(`Buy subscription for ${planId.replace('_', ' ')}?`, async (confirmed) => {
            if (confirmed) {
                try {
                    // Show loading
                    tg.MainButton.showProgress();

                    const result = await state.user.functions.buySubscription(planId);

                    tg.MainButton.hideProgress();

                    if (result.success) {
                        appLogic.showToast("Subscription purchased!");
                        await appLogic.loadProfile();
                        router.navigate('home');
                        // Show config info immediately if needed
                    }
                } catch (err) {
                    tg.MainButton.hideProgress();
                    console.error("Buy Sub Error:", err);
                    tg.showAlert(`Error: ${err.message}`); // Atlas function errors usually come as text
                }
            }
        });
    },

    createPayment: async () => {
        const amount = document.getElementById('topup-amount').value;
        if (!amount || amount < 50) {
            appLogic.showToast("Minimum amount is 50 ₽");
            return;
        }

        try {
             // Show loading
            const btn = event.target;
            const originalText = btn.innerText;
            btn.innerText = "Generating Link...";
            btn.disabled = true;

            const result = await state.user.functions.createPayment(Number(amount), "Balance Top-up");

            if (result.confirmation_url) {
                // Open payment link
                window.Telegram.WebApp.openLink(result.confirmation_url);
            }

            btn.innerText = originalText;
            btn.disabled = false;

        } catch (err) {
            console.error("Payment Error:", err);
            appLogic.showToast("Payment creation failed");
             // Reset button
            const btn = document.querySelector('#topup-view button.bg-green-600'); // dirty selector, better use ID
             if (btn) {
                 btn.innerText = "Pay securely";
                 btn.disabled = false;
             }
        }
    },

    loadConfigs: async () => {
        if (!state.user) return;
        const list = document.getElementById('configs-list');
        list.innerHTML = '<p class="text-center text-gray-400">Loading configs...</p>';

        try {
            const configs = await state.user.functions.getConfigs();
            state.configs = configs;

            list.innerHTML = '';

            if (configs.length === 0) {
                list.innerHTML = `<div class="text-center text-gray-500 py-10">
                    <p>No active configurations.</p>
                    <button onclick="router.navigate('shop')" class="text-blue-600 font-medium mt-2">Get one now</button>
                </div>`;
                return;
            }

            configs.forEach(config => {
                const el = document.createElement('div');
                el.className = 'bg-white p-4 rounded-xl shadow-sm border border-gray-100';
                el.innerHTML = `
                    <div class="flex justify-between items-start mb-2">
                        <h3 class="font-bold text-gray-800">${config.name}</h3>
                        <span class="text-xs text-gray-400">${new Date(config.assigned_at).toLocaleDateString()}</span>
                    </div>
                    <div class="bg-gray-50 p-2 rounded text-xs font-mono break-all text-gray-600 select-all cursor-pointer hover:bg-gray-100" onclick="appLogic.copyText('${config.link}')">
                        ${config.link.substring(0, 40)}...
                    </div>
                    <div class="mt-2 text-right">
                        <button onclick="appLogic.copyText('${config.link}')" class="text-blue-600 text-sm font-medium">Copy Link</button>
                    </div>
                `;
                list.appendChild(el);
            });

        } catch (err) {
            console.error("Load Configs Error:", err);
            list.innerHTML = '<p class="text-center text-red-500">Failed to load configs.</p>';
        }
    },

    loadReferral: () => {
         if (!state.user) return;
         // Generate referral link based on user ID
         const botUsername = "vpni50_bot"; // Replace with actual bot username
         const link = `https://t.me/${botUsername}?start=${state.user.id}`;
         document.getElementById('referral-link').innerText = link;
    },

    copyReferral: () => {
        const text = document.getElementById('referral-link').innerText;
        appLogic.copyText(text);
    },

    copyText: (text) => {
        navigator.clipboard.writeText(text).then(() => {
            appLogic.showToast("Copied to clipboard!");
        }).catch(err => {
            console.error('Async: Could not copy text: ', err);
        });
    },

    showToast: (msg) => {
        const toast = document.getElementById('toast');
        toast.innerText = msg;
        toast.classList.remove('opacity-0');
        setTimeout(() => {
            toast.classList.add('opacity-0');
        }, 3000);
    }
};

// Expose to window for onclick handlers
window.app = appLogic;
window.router = router;

// Start
document.addEventListener('DOMContentLoaded', appLogic.init);
