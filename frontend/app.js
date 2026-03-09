const APP_ID = "YOUR_APP_ID"; // TODO: Replace with actual Realm App ID
const app = new Realm.App({ id: APP_ID });

let tg = window.Telegram.WebApp;
tg.expand();

let currentUserData = null;

// Utility functions
function showToast(message, type = 'error') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `fixed bottom-4 left-4 right-4 text-white p-3 rounded-xl shadow-lg transform transition-all duration-300 z-50 text-center font-medium ${type === 'error' ? 'bg-red-500' : 'bg-green-500'}`;

    // Show
    toast.classList.remove('translate-y-20', 'opacity-0');
    toast.classList.add('translate-y-0', 'opacity-100');

    // Hide
    setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('translate-y-20', 'opacity-0');
    }, 3000);
}

function nav(pageId) {
    document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');

    if (pageId === 'page-home') {
        tg.BackButton.hide();
    } else {
        tg.BackButton.show();
        tg.BackButton.onClick(() => nav('page-home'));
    }
}

// Authentication
async function authenticate() {
    try {
        let initData = tg.initData;
        let telegramId = "mock_user_123";
        let isLocalMock = false;

        // Fallback for local testing if not running in Telegram
        if (!initData && (window.location.hostname === 'localhost' || window.location.protocol === 'file:')) {
            console.log("Running locally, using mock initData");
            initData = "query_id=mock123&user=%7B%22id%22%3A123456789%2C%22first_name%22%3A%22Local%22%2C%22last_name%22%3A%22Tester%22%2C%22username%22%3A%22local_tester%22%2C%22language_code%22%3A%22en%22%7D&auth_date=1690000000&hash=mockhash";
            telegramId = "123456789";
            isLocalMock = true;
        }

        if (!initData) {
            throw new Error("Cannot authenticate: No Telegram initData available.");
        }

        if (!isLocalMock) {
            // Use custom function authentication
            const credentials = Realm.Credentials.function({ initData: initData });
            const user = await app.logIn(credentials);
            console.log("Successfully logged in:", user.id);
        } else {
            console.log("Skipping actual Realm login due to local mock mode.");
        }

        // After login, fetch profile data
        await loadProfile(telegramId, isLocalMock);
        await loadConfigs(isLocalMock);

        // Hide loading, show app
        document.getElementById('loading-screen').style.opacity = '0';
        setTimeout(() => {
            document.getElementById('loading-screen').style.display = 'none';
            document.getElementById('app').classList.remove('hidden');
        }, 300);

    } catch (err) {
        console.error("Auth error:", err);
        showToast("Authentication failed.");
    }
}

// Profile Loading
async function loadProfile(telegramId, isLocalMock = false) {
    try {
        let profile;
        if (!isLocalMock && app.currentUser && app.currentUser.functions) {
             profile = await app.currentUser.functions.getProfile(telegramId);
        } else {
             // Mock profile for local testing without valid Realm App
             profile = {
                 first_name: "Local Tester",
                 balance: 150,
                 days_left: 0,
                 referrals_count: 2,
                 used_configs: []
             };
        }

        currentUserData = profile;

        // Update UI
        document.getElementById('greeting').textContent = `Hello, ${profile.first_name}!`;
        document.getElementById('user-balance').textContent = profile.balance;

        const statusEl = document.getElementById('sub-status');
        const detailsEl = document.getElementById('sub-details');

        if (profile.days_left > 0) {
            statusEl.textContent = "Active";
            statusEl.classList.add('text-green-500');
            statusEl.classList.remove('text-red-500');
            detailsEl.innerHTML = `Active for <span class="font-bold text-green-500">${profile.days_left}</span> more days.<br><span class="text-xs hint-color">Until: ${new Date(profile.subscription_end).toLocaleDateString()}</span>`;
        } else {
            statusEl.textContent = "Inactive";
            statusEl.classList.add('text-red-500');
            statusEl.classList.remove('text-green-500');
            detailsEl.textContent = "You don't have an active subscription yet.";
        }

        // Update referrals
        document.getElementById('ref-count').textContent = profile.referrals_count;
        document.getElementById('ref-link').textContent = `https://t.me/vpni50_bot?start=${telegramId}`;

        // Update configs list
        renderUserConfigs(profile.used_configs);

    } catch (err) {
        console.error("Profile load error:", err);
        showToast("Failed to load profile.");
    }
}

function renderUserConfigs(configs) {
    const list = document.getElementById('user-configs-list');
    list.innerHTML = '';

    if (!configs || configs.length === 0) {
        list.innerHTML = '<p class="text-center hint-color text-sm mt-4">You have no configurations yet.</p>';
        return;
    }

    configs.forEach(conf => {
        const div = document.createElement('div');
        div.className = 'secondary-bg p-4 rounded-xl relative';
        div.innerHTML = `
            <h3 class="font-bold">${conf.config_name} <span class="text-xs font-normal hint-color ml-2">${conf.period}</span></h3>
            <p class="text-xs hint-color mb-2">Issued: ${conf.issue_date}</p>
            <div class="flex items-center gap-2">
                <input type="text" readonly value="${conf.config_link}" class="w-full text-xs p-2 rounded bg-white dark:bg-gray-800 border-none outline-none">
                <button onclick="navigator.clipboard.writeText('${conf.config_link}'); showToast('Copied!', 'success');" class="button p-2 rounded text-xs shrink-0">Copy</button>
            </div>
        `;
        list.appendChild(div);
    });
}

// Configs Loading
async function loadConfigs(isLocalMock = false) {
    try {
        let periods;
        if (!isLocalMock && app.currentUser && app.currentUser.functions) {
            periods = await app.currentUser.functions.getConfigs();
        } else {
            // Mock periods for local testing
            periods = {
                '1_month': { price: 50, days: 30 },
                '2_months': { price: 90, days: 60 },
                '3_months': { price: 120, days: 90 }
            };
        }

        const list = document.getElementById('configs-list');
        list.innerHTML = '';

        for (const [key, data] of Object.entries(periods)) {
            const div = document.createElement('div');
            div.className = 'secondary-bg p-4 rounded-xl flex justify-between items-center';
            div.innerHTML = `
                <div>
                    <h3 class="font-bold">${data.days} Days</h3>
                    <p class="text-sm font-medium text-blue-500">${data.price} ₽</p>
                </div>
                <button onclick="buySub('${key}', ${data.price})" class="button px-4 py-2 rounded-lg font-bold">Buy</button>
            `;
            list.appendChild(div);
        }
    } catch (err) {
        console.error("Configs load error:", err);
    }
}

// Purchasing
async function buySub(periodKey, price) {
    if (!currentUserData) return;

    if (currentUserData.balance < price) {
        showToast(`Insufficient balance. You need ${price} ₽.`);
        nav('page-topup');
        return;
    }

    tg.showConfirm(`Buy subscription for ${price} ₽?`, async (confirmed) => {
        if (!confirmed) return;

        try {
            tg.MainButton.showProgress();

            let result;
            const isLocalMock = (!tg.initData && (window.location.hostname === 'localhost' || window.location.protocol === 'file:'));

            if (!isLocalMock && app.currentUser && app.currentUser.functions) {
                // Determine telegram ID from initData or fallback
                let telegramId = "123456789";
                if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                    telegramId = tg.initDataUnsafe.user.id.toString();
                }

                result = await app.currentUser.functions.buySubscription(telegramId, periodKey);
            } else {
                 // Mock result
                 await new Promise(r => setTimeout(r, 1000));
                 result = { success: true, message: "Mock purchased." };
            }

            if (result.success) {
                showToast("Purchase successful!", "success");
                tg.HapticFeedback.notificationOccurred("success");

                // Refresh profile data
                let telegramId = "123456789";
                if (tg.initDataUnsafe && tg.initDataUnsafe.user) telegramId = tg.initDataUnsafe.user.id.toString();
                await loadProfile(telegramId, isLocalMock);

                nav('page-configs');
            } else {
                showToast(result.message || "Purchase failed.");
                tg.HapticFeedback.notificationOccurred("error");
            }
        } catch (err) {
            console.error("Buy error:", err);
            showToast("An error occurred during purchase.");
        } finally {
            tg.MainButton.hideProgress();
        }
    });
}

// Topup
function setTopupAmount(amount) {
    document.getElementById('custom-amount').value = amount;
}

async function processTopup() {
    const input = document.getElementById('custom-amount').value;
    const amount = parseInt(input);

    if (isNaN(amount) || amount < 50) {
        showToast("Minimum topup amount is 50 ₽.");
        return;
    }

    const btnText = document.getElementById('topup-btn-text');
    const spinner = document.getElementById('topup-spinner');

    btnText.textContent = 'Processing...';
    spinner.classList.remove('hidden');

    try {
        let telegramId = "123456789";
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) telegramId = tg.initDataUnsafe.user.id.toString();
        const isLocalMock = (!tg.initData && (window.location.hostname === 'localhost' || window.location.protocol === 'file:'));

        if (!isLocalMock && app.currentUser && app.currentUser.functions) {
            const result = await app.currentUser.functions.createPayment(telegramId, amount);
            if (result.success && result.confirmation_url) {
                // Open payment URL in Telegram browser
                tg.openLink(result.confirmation_url);

                // Start checking payment status
                checkPaymentStatus(telegramId, result.payment_id);
            } else {
                showToast(result.message || "Failed to create payment.");
            }
        } else {
            // Mock
            await new Promise(r => setTimeout(r, 1000));
            showToast("Mock payment created.", "success");
        }
    } catch (err) {
        console.error("Topup error:", err);
        showToast("An error occurred.");
    } finally {
        btnText.textContent = 'Pay';
        spinner.classList.add('hidden');
    }
}

function copyRefLink() {
    const link = document.getElementById('ref-link').textContent;
    navigator.clipboard.writeText(link);
    showToast("Referral link copied!", "success");
}

// Polling for payment status
async function checkPaymentStatus(telegramId, paymentId) {
    const maxAttempts = 20; // e.g. poll every 5s for ~1.5 mins
    let attempts = 0;

    const interval = setInterval(async () => {
        attempts++;
        if (attempts > maxAttempts) {
            clearInterval(interval);
            return;
        }

        try {
            const res = await app.currentUser.functions.checkPayment(telegramId, paymentId);
            if (res.success) {
                clearInterval(interval);
                showToast("Payment confirmed! Balance updated.", "success");
                tg.HapticFeedback.notificationOccurred("success");
                await loadProfile(telegramId, false);
                nav('page-home');
            }
        } catch (e) {
            console.error("Check payment error", e);
        }
    }, 5000);
}

// Initialize
tg.ready();
authenticate();