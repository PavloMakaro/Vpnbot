// IMPORTANT: Replace with your actual App ID from MongoDB Atlas App Services
const APP_ID = "application-0-xxxxx";

// Initialize Realm App
const app = new Realm.App({ id: APP_ID });

// Telegram WebApp
const telegram = window.Telegram.WebApp;
telegram.expand();

// Determine theme colors (optional, for advanced integration)
// const themeParams = telegram.themeParams;

const App = {
    user: null,

    init: async () => {
        try {
            // Check if initData is available
            if (!telegram.initData) {
                console.warn("No initData found. Authentication might fail if running outside Telegram.");
            }

            // Authenticate with Atlas Custom Function Auth
            const credentials = Realm.Credentials.function({
                initData: telegram.initData
            });

            App.user = await app.logIn(credentials);
            console.log("Logged in successfully. User ID:", App.user.id);

            await App.loadUserData();

            // Show Home View
            document.getElementById('loader').classList.add('hidden');
            document.getElementById('view-home').classList.remove('hidden');

            // Setup Back Button
            telegram.BackButton.onClick(() => {
                App.showView('view-home');
            });

        } catch (error) {
            console.error("Login failed:", error);
            document.getElementById('loader').innerHTML = `<div class="text-red-500 text-center p-4">Login failed.<br>${error.message}</div>`;
        }
    },

    loadUserData: async () => {
        try {
            const userProfile = await App.user.functions.getUser();

            // Update UI
            document.getElementById('user-name').textContent = userProfile.first_name || 'User';
            document.getElementById('user-username').textContent = userProfile.username ? '@' + userProfile.username : 'No username';
            document.getElementById('user-balance').textContent = (userProfile.balance || 0).toLocaleString('ru-RU') + ' ₽';

            // Avatar
            const firstLetter = (userProfile.first_name || 'U').charAt(0).toUpperCase();
            document.getElementById('user-avatar').textContent = firstLetter;

            // Subscription status
            const subEnd = userProfile.subscription_end ? new Date(userProfile.subscription_end) : null;
            const now = new Date();
            const subBadge = document.getElementById('user-subscription');

            if (subEnd && subEnd > now) {
                const daysLeft = Math.ceil((subEnd - now) / (1000 * 60 * 60 * 24));
                subBadge.textContent = `Active (${daysLeft} days)`;
                subBadge.className = 'text-sm font-medium px-2 py-1 rounded bg-green-600 text-white';
            } else {
                subBadge.textContent = 'Inactive';
                subBadge.className = 'text-sm font-medium px-2 py-1 rounded bg-gray-600 text-gray-300';
            }
        } catch (error) {
            console.error("Failed to load user data:", error);
            App.showToast("Failed to update profile");
        }
    },

    showView: async (viewId) => {
        // Hide all views
        document.querySelectorAll('.view').forEach(el => el.classList.add('hidden'));

        // Show target view
        const target = document.getElementById(viewId);
        target.classList.remove('hidden');

        // Handle Back Button visibility
        const customBackBtn = document.getElementById('back-button-container');
        if (viewId === 'view-home') {
            telegram.BackButton.hide();
            if (customBackBtn) customBackBtn.classList.add('hidden');
        } else {
            telegram.BackButton.show();
            if (customBackBtn) customBackBtn.classList.remove('hidden');
        }

        // Load data for specific views
        if (viewId === 'view-buy') {
            await App.loadPlans();
        } else if (viewId === 'view-configs') {
            await App.loadConfigs();
        } else if (viewId === 'view-home') {
            // Refresh user data when returning home
            await App.loadUserData();
        }
    },

    createPayment: async () => {
        const input = document.getElementById('topup-amount');
        const amount = parseFloat(input.value);

        if (!amount || amount < 50) {
            App.showToast("Minimum amount is 50 ₽");
            return;
        }

        try {
            App.showToast("Creating payment...");
            // Call Atlas Function
            const url = await App.user.functions.createPayment(amount);

            // Open payment link
            telegram.openLink(url);

            // Optimistic UI update or instruction
            App.showToast("Payment page opened. Balance will update automatically.");

        } catch (error) {
            console.error("Payment error:", error);
            App.showToast("Error: " + error.message);
        }
    },

    loadPlans: async () => {
        const container = document.getElementById('plans-container');
        container.innerHTML = '<div class="text-center py-4"><div class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mx-auto"></div></div>';

        try {
            const plans = await App.user.functions.getConfigs();
            container.innerHTML = '';

            if (plans.length === 0) {
                container.innerHTML = '<p class="text-gray-400 text-center">No plans available at the moment.</p>';
                return;
            }

            plans.forEach(plan => {
                const card = document.createElement('div');
                card.className = 'bg-gray-800 rounded-xl p-4 flex justify-between items-center shadow-md border border-gray-700';
                card.innerHTML = `
                    <div>
                        <h3 class="font-bold text-lg">${plan.label || plan.id}</h3>
                        <p class="text-sm text-gray-400">${plan.available} configs available</p>
                    </div>
                    <div class="text-right">
                        <p class="font-bold text-xl text-green-400 mb-1">${plan.price} ₽</p>
                        <button onclick="App.buySubscription('${plan.id}', ${plan.price})"
                                class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold py-2 px-4 rounded-lg transition transform active:scale-95 ${plan.available === 0 ? 'opacity-50 cursor-not-allowed' : ''}"
                                ${plan.available === 0 ? 'disabled' : ''}>
                            Buy
                        </button>
                    </div>
                `;
                container.appendChild(card);
            });
        } catch (error) {
            container.innerHTML = `<p class="text-red-400 text-center">Failed to load plans: ${error.message}</p>`;
        }
    },

    buySubscription: async (periodId, price) => {
        // Confirmation
        telegram.showPopup({
            title: 'Confirm Purchase',
            message: `Buy subscription for ${price} ₽?`,
            buttons: [
                {id: 'buy', type: 'ok', text: 'Buy'},
                {id: 'cancel', type: 'cancel'}
            ]
        }, async (buttonId) => {
            if (buttonId === 'buy') {
                try {
                    App.showToast("Processing...");
                    const result = await App.user.functions.buySubscription(periodId);

                    if (result.success) {
                        telegram.showAlert(`Success! Your subscription is active until ${new Date(result.new_end_date).toLocaleDateString()}`);
                        await App.loadUserData();
                        App.showView('view-home');
                    }
                } catch (error) {
                    telegram.showAlert(`Error: ${error.message}`);
                    App.showToast(error.message);
                }
            }
        });
    },

    loadConfigs: async () => {
        const container = document.getElementById('configs-container');
        container.innerHTML = '<div class="text-center py-4"><div class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mx-auto"></div></div>';

        try {
            const configs = await App.user.functions.getUserConfigs();
            container.innerHTML = '';

            if (!configs || configs.length === 0) {
                container.innerHTML = '<p class="text-gray-400 text-center py-8">You don\'t have any configs yet.<br>Buy a subscription to get one!</p>';
                return;
            }

            // Sort by issue date descending
            configs.sort((a, b) => new Date(b.issue_date) - new Date(a.issue_date));

            configs.forEach(config => {
                const card = document.createElement('div');
                card.className = 'bg-gray-800 rounded-xl p-4 mb-3 shadow-md border border-gray-700 relative overflow-hidden';

                const dateStr = new Date(config.issue_date).toLocaleDateString();

                card.innerHTML = `
                    <div class="flex justify-between items-start mb-2">
                        <div>
                            <h3 class="font-bold text-white">${config.config_name}</h3>
                            <p class="text-xs text-gray-400">${config.period} • Issued: ${dateStr}</p>
                        </div>
                    </div>
                    <div class="bg-gray-900 rounded p-2 mb-3 font-mono text-xs text-gray-300 break-all h-16 overflow-hidden relative">
                        ${config.config_link.substring(0, 100)}...
                        <div class="absolute inset-0 bg-gradient-to-b from-transparent to-gray-900 pointer-events-none"></div>
                    </div>
                    <button onclick="App.copyToClipboard('${config.config_link}')" class="w-full bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded-lg flex items-center justify-center transition active:scale-95">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
                        Copy Link
                    </button>
                `;
                container.appendChild(card);
            });
        } catch (error) {
            container.innerHTML = `<p class="text-red-400 text-center">Failed to load configs: ${error.message}</p>`;
        }
    },

    copyToClipboard: (text) => {
        navigator.clipboard.writeText(text).then(() => {
            App.showToast("Copied to clipboard!");
            // Haptic feedback
            if (telegram.HapticFeedback) {
                telegram.HapticFeedback.notificationOccurred('success');
            }
        }).catch(err => {
            console.error('Async: Could not copy text: ', err);
            // Fallback for older browsers if needed
            App.showToast("Failed to copy");
        });
    },

    showToast: (message) => {
        const toast = document.getElementById('toast');
        const msg = document.getElementById('toast-message');
        if (msg) msg.textContent = message;

        toast.classList.remove('hidden');
        toast.classList.add('toast-enter');

        setTimeout(() => {
            toast.classList.remove('toast-enter');
            toast.classList.add('toast-exit');
            setTimeout(() => {
                toast.classList.add('hidden');
                toast.classList.remove('toast-exit');
            }, 300);
        }, 3000);
    }
};

// Start the app
window.addEventListener('load', App.init);
