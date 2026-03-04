const APP_ID = "YOUR_ATLAS_APP_ID"; // Replace with your real Atlas App ID

let app;
let userProfile;
const tg = window.Telegram.WebApp;

// Initialize
async function init() {
    tg.ready();
    tg.expand();

    app = new Realm.App({ id: APP_ID });

    try {
        await login();
        await loadProfile();
        setupEventListeners();
    } catch (err) {
        console.error("Initialization error:", err);
        tg.showAlert("Failed to initialize app: " + err.message);
    }
}

async function login() {
    showLoading();
    try {
        const initData = tg.initData || "dummy_init_data_for_local_testing"; // Fallback for testing

        let loginPayload = { initData: initData };
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            loginPayload.user = JSON.stringify(tg.initDataUnsafe.user);
        }

        const credentials = Realm.Credentials.function(loginPayload);
        await app.logIn(credentials);
        console.log("Logged in successfully!", app.currentUser.id);
    } finally {
        hideLoading();
    }
}

async function loadProfile() {
    showLoading();
    try {
        userProfile = await app.currentUser.functions.getProfile();

        document.getElementById('welcome-message').innerText = `Привет, ${userProfile.first_name}!`;
        document.getElementById('balance-value').innerText = userProfile.balance;

        let subStatus = "Нет";
        if (userProfile.subscription_end) {
            const endDate = new Date(userProfile.subscription_end);
            if (endDate > new Date()) {
                subStatus = `Активна до ${endDate.toLocaleDateString()}`;
            } else {
                subStatus = "Истекла";
            }
        }
        document.getElementById('subscription-status').innerText = subStatus;

        renderMyConfigs();

        showSection('profile-section');
        document.getElementById('my-configs-section').style.display = 'block';
    } catch (err) {
        console.error("Error loading profile:", err);
        tg.showAlert("Could not load profile");
    } finally {
        hideLoading();
    }
}

function renderMyConfigs() {
    const list = document.getElementById('my-configs-list');
    list.innerHTML = '';

    if (!userProfile.used_configs || userProfile.used_configs.length === 0) {
        list.innerHTML = '<p class="text-gray-500">У вас пока нет выданных конфигов.</p>';
        return;
    }

    userProfile.used_configs.forEach(config => {
        const div = document.createElement('div');
        div.className = 'p-3 bg-gray-50 dark:bg-gray-700 rounded border dark:border-gray-600 break-all';
        div.innerHTML = `
            <p class="font-medium">${config.config_name} (${config.period})</p>
            <p class="text-sm text-gray-500 dark:text-gray-400 mb-2">Выдан: ${config.issue_date}</p>
            <code class="text-xs text-blue-600 dark:text-blue-400 select-all">${config.config_link}</code>
        `;
        list.appendChild(div);
    });
}

async function loadConfigsForSale() {
    showLoading();
    try {
        const configs = await app.currentUser.functions.getConfigs();
        const list = document.getElementById('configs-list');
        list.innerHTML = '';

        for (const [period, data] of Object.entries(configs)) {
            const btn = document.createElement('button');
            btn.className = 'w-full text-left p-3 rounded border dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 flex justify-between items-center';
            btn.innerHTML = `
                <span>${data.days} дней</span>
                <span class="font-bold text-green-600 dark:text-green-400">${data.price} ₽</span>
            `;
            btn.onclick = () => buySubscription(period, data.price);
            list.appendChild(btn);
        }
    } catch (err) {
        console.error("Error loading configs:", err);
        tg.showAlert("Failed to load subscription options");
    } finally {
        hideLoading();
    }
}

async function buySubscription(period, price) {
    if (userProfile.balance < price) {
        tg.showAlert("Недостаточно средств на балансе. Пожалуйста, пополните счет.");
        showSection('topup-section');
        return;
    }

    tg.showConfirm(`Купить подписку на ${period.replace('_', ' ')} за ${price} ₽?`, async (confirmed) => {
        if (!confirmed) return;

        showLoading();
        try {
            const result = await app.currentUser.functions.buySubscription(period);
            if (result.success) {
                tg.showAlert("Успешно куплено!");
                await loadProfile();
                showSection('profile-section');
            }
        } catch (err) {
            console.error("Purchase error:", err);
            tg.showAlert(err.message || "Ошибка при покупке. Попробуйте позже.");
        } finally {
            hideLoading();
        }
    });
}

async function createTopupPayment(amount) {
    showLoading();
    try {
        const result = await app.currentUser.functions.createPayment(amount, `Пополнение баланса на ${amount} ₽`, window.location.href);

        // Open the payment URL in the Telegram Web App browser
        tg.openLink(result.confirmationUrl);

        // Polling to check payment status
        const pollInterval = setInterval(async () => {
            try {
                const check = await app.currentUser.functions.checkPayment(result.paymentId);
                if (check.status === "succeeded") {
                    clearInterval(pollInterval);
                    tg.showAlert("Баланс успешно пополнен!");
                    await loadProfile();
                    showSection('profile-section');
                } else if (check.status === "canceled") {
                    clearInterval(pollInterval);
                    tg.showAlert("Платеж отменен.");
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 5000);

    } catch (err) {
        console.error("Topup error:", err);
        tg.showAlert("Ошибка создания платежа: " + err.message);
        hideLoading(); // Only hide on error, if success we keep loading or switch section
    }
}

// UI Helpers
function setupEventListeners() {
    document.getElementById('btn-buy').addEventListener('click', () => {
        loadConfigsForSale();
        showSection('buy-section');
    });

    document.getElementById('btn-topup').addEventListener('click', () => {
        showSection('topup-section');
    });

    document.getElementById('btn-back-buy').addEventListener('click', () => {
        showSection('profile-section');
    });

    document.getElementById('btn-back-topup').addEventListener('click', () => {
        showSection('profile-section');
    });

    document.querySelectorAll('.topup-amount').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const amount = parseInt(e.target.dataset.amount);
            createTopupPayment(amount);
        });
    });
}

function showSection(sectionId) {
    ['profile-section', 'buy-section', 'topup-section'].forEach(id => {
        document.getElementById(id).style.display = id === sectionId ? 'block' : 'none';
    });
    // My configs should be visible when profile is visible
    document.getElementById('my-configs-section').style.display = sectionId === 'profile-section' ? 'block' : 'none';
}

function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// Start
init();
