// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Configuration - Replace with your Atlas App ID
const REALM_APP_ID = 'application-0-xyz';
let app, user;

// Mock Data for Development (since backend isn't live)
const MOCK_MODE = true;
let mockUser = {
    id: tg.initDataUnsafe?.user?.id || 123456789,
    username: tg.initDataUnsafe?.user?.username || 'test_user',
    first_name: tg.initDataUnsafe?.user?.first_name || 'Test User',
    balance: 100,
    subscription_end: null, // "2023-12-31T23:59:59"
    referral_count: 5,
    referral_earnings: 250,
    configs: []
};

// UI Elements
const els = {
    userName: document.getElementById('user-name'),
    userId: document.getElementById('user-id'),
    userBalance: document.getElementById('user-balance'),
    subStatus: document.getElementById('subscription-status'),
    subDate: document.getElementById('subscription-date'),
    referralLink: document.getElementById('referral-link'),
    referralCount: document.getElementById('referral-count'),
    referralEarnings: document.getElementById('referral-earnings'),
    modal: document.getElementById('modal-confirm'),
    modalPeriod: document.getElementById('modal-period'),
    modalPrice: document.getElementById('modal-price'),
    toast: document.getElementById('toast'),
    toastMsg: document.getElementById('toast-message'),
    customAmount: document.getElementById('custom-amount')
};

// Initialize App
async function init() {
    // Set theme colors based on Telegram theme
    document.body.style.backgroundColor = tg.themeParams.bg_color || '#111827';
    document.body.style.color = tg.themeParams.text_color || '#ffffff';

    if (MOCK_MODE) {
        console.log("Running in MOCK MODE");
        renderUser(mockUser);
        loadConfigs(); // Load mock configs
    } else {
        try {
            app = new Realm.App({ id: REALM_APP_ID });
            // Authenticate anonymously or via Custom Function using initData
            // For simplicity, we'll assume Custom Function Auth here
            const credentials = Realm.Credentials.function({ initData: tg.initData });
            user = await app.logIn(credentials);
            console.log("Logged in to Atlas:", user.id);
            await refreshData();
        } catch (err) {
            console.error("Failed to log in", err);
            showToast("Failed to connect to server");
        }
    }
}

// Fetch User Data
async function refreshData() {
    if (MOCK_MODE) return;
    try {
        const profile = await user.functions.getUserProfile();
        renderUser(profile);
        loadConfigs();
    } catch (err) {
        console.error("Failed to fetch profile", err);
    }
}

// Render User Interface
function renderUser(userData) {
    els.userName.textContent = userData.first_name;
    els.userId.textContent = userData.id;
    els.userBalance.textContent = userData.balance;

    // Subscription Status
    const now = new Date();
    const subEnd = userData.subscription_end ? new Date(userData.subscription_end) : null;

    if (subEnd && subEnd > now) {
        els.subStatus.innerHTML = `<span class="w-3 h-3 rounded-full bg-green-500"></span><span class="font-medium text-lg text-green-400">Active</span>`;
        els.subDate.textContent = `Valid until ${subEnd.toLocaleDateString()}`;
    } else {
        els.subStatus.innerHTML = `<span class="w-3 h-3 rounded-full bg-red-500"></span><span class="font-medium text-lg text-red-400">Inactive</span>`;
        els.subDate.textContent = "No active subscription";
    }

    // Referrals
    els.referralCount.textContent = userData.referral_count || 0;
    els.referralEarnings.textContent = (userData.referral_earnings || 0) + ' ₽';
    els.referralLink.value = `https://t.me/YourBotName?start=${userData.id}`; // Replace with actual bot username
}

// Tab Switching
window.switchTab = (tabId) => {
    document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.add('hidden');
        el.classList.remove('active');
    });
    document.getElementById(`tab-${tabId}`).classList.remove('hidden');
    // minimal delay to allow display:block to apply before opacity transition
    setTimeout(() => {
         document.getElementById(`tab-${tabId}`).classList.add('active');
    }, 10);


    // Update Bottom Nav
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active', 'text-blue-500');
        btn.classList.add('text-gray-400');
    });
    // Highlight current tab button (naive implementation relying on order)
    // A better way is to add IDs to buttons.
    // For now, let's just use the onclick handler to set active class on the clicked button
    const btn = event.currentTarget;
    if (btn) {
        btn.classList.add('active', 'text-blue-500');
        btn.classList.remove('text-gray-400');
    }
};
// Attach event listener to first tab button to set initial active state
document.querySelector('.nav-btn').click();


// Purchase Flow
let selectedPlan = null;

window.selectPlan = (period, price) => {
    selectedPlan = { period, price };
    els.modalPeriod.textContent = period.replace('_', ' ');
    els.modalPrice.textContent = price + ' ₽';
    els.modal.classList.remove('hidden');
    setTimeout(() => els.modal.classList.add('show'), 10);
};

window.closeModal = () => {
    els.modal.classList.remove('show');
    setTimeout(() => els.modal.classList.add('hidden'), 300);
    selectedPlan = null;
};

window.confirmPurchase = async () => {
    if (!selectedPlan) return;

    // Check balance locally first
    const currentBalance = parseInt(els.userBalance.textContent);
    if (currentBalance < selectedPlan.price) {
        showToast("Insufficient balance! Please Top Up.");
        closeModal();
        switchTab('topup'); // Switch to Top Up tab
        return;
    }

    if (MOCK_MODE) {
        mockUser.balance -= selectedPlan.price;
        const days = selectedPlan.period === '1_month' ? 30 : selectedPlan.period === '2_months' ? 60 : 90;
        const now = new Date();
        const currentEnd = mockUser.subscription_end ? new Date(mockUser.subscription_end) : now;
        const start = currentEnd > now ? currentEnd : now;
        start.setDate(start.getDate() + days);
        mockUser.subscription_end = start.toISOString();

        // Add a mock config
        mockUser.configs.push({
            name: `Config ${mockUser.configs.length + 1}`,
            period: selectedPlan.period,
            date: new Date().toLocaleDateString(),
            link: "vless://mock-link..."
        });

        renderUser(mockUser);
        loadConfigs();
        showToast("Subscription Activated!");
    } else {
        try {
            const result = await user.functions.buySubscription(selectedPlan.period);
            if (result.success) {
                showToast("Subscription Activated!");
                await refreshData();
            } else {
                showToast(result.error || "Purchase failed");
            }
        } catch (err) {
            console.error("Purchase error", err);
            showToast("An error occurred");
        }
    }
    closeModal();
};

// Top Up Logic
window.setTopUpAmount = (amount) => {
    els.customAmount.value = amount;
};

window.initiateTopUp = async () => {
    const amount = parseInt(els.customAmount.value);
    if (!amount || amount < 50) {
        showToast("Minimum amount is 50 ₽");
        return;
    }

    if (MOCK_MODE) {
        // Simulate payment success
        showToast(`Top Up of ${amount} ₽ initiated (Mock)`);
        setTimeout(() => {
            mockUser.balance += amount;
            renderUser(mockUser);
            showToast("Balance Updated!");
        }, 1500);
    } else {
        try {
            const paymentUrl = await user.functions.createPayment(amount);
            if (paymentUrl) {
                tg.openLink(paymentUrl); // Open Yookassa in browser
            } else {
                showToast("Failed to create payment");
            }
        } catch (err) {
            console.error("Topup error", err);
            showToast("Error initiating payment");
        }
    }
};

// Load Configs
async function loadConfigs() {
    const container = document.getElementById('configs-list');
    container.innerHTML = '';

    let configs = [];
    if (MOCK_MODE) {
        configs = mockUser.configs;
    } else {
        configs = await user.functions.getConfigs();
    }

    if (configs.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 py-8">No active configs found. Buy a subscription to get one!</div>';
        return;
    }

    configs.forEach(conf => {
        const div = document.createElement('div');
        div.className = 'bg-gray-800 rounded-xl p-4 border border-gray-700 flex justify-between items-center';
        div.innerHTML = `
            <div>
                <h3 class="font-bold text-blue-400">${conf.name || 'VPN Config'}</h3>
                <p class="text-xs text-gray-500">${conf.period} • ${conf.date}</p>
            </div>
            <button onclick="copyToClipboard('${conf.link}')" class="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm transition">
                Copy Link
            </button>
        `;
        container.appendChild(div);
    });
}

// Utilities
window.copyReferral = () => {
    const link = els.referralLink.value;
    copyToClipboard(link);
};

window.copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
        showToast("Copied to clipboard!");
    }).catch(() => {
        showToast("Failed to copy");
    });
};

function showToast(msg) {
    els.toastMsg.textContent = msg;
    els.toast.classList.remove('hidden');
    setTimeout(() => els.toast.classList.add('show'), 10);

    setTimeout(() => {
        els.toast.classList.remove('show');
        setTimeout(() => els.toast.classList.add('hidden'), 300);
    }, 3000);
}

// Start
init();
