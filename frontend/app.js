// Constants
const APP_ID = "YOUR_APP_ID"; // Replace with actual Realm App ID during deployment

// DOM Elements
const appDiv = document.getElementById('app');
const loaderDiv = document.getElementById('loader');
const balanceEl = document.getElementById('user-balance');
const subEl = document.getElementById('user-subscription');
const refEl = document.getElementById('user-referrals');
const configsListEl = document.getElementById('configs-list');
const toastEl = document.getElementById('toast');
const toastMsg = document.getElementById('toast-message');

// Navigation Buttons
const btnTopup = document.getElementById('btn-topup');
const btnBuy = document.getElementById('btn-buy');
const viewHome = document.getElementById('view-home');
const viewBuy = document.getElementById('view-buy');
const viewTopup = document.getElementById('view-topup');
const btnBackBuy = document.getElementById('btn-back-buy');
const btnBackTopup = document.getElementById('btn-back-topup');
const btnPay = document.getElementById('btn-pay');
const topupAmount = document.getElementById('topup-amount');
const subOptionsEl = document.getElementById('subscription-options');

// State
let app;
let currentUser;
let userProfile;
let subscriptionConfigs = {};

// Initialize App
async function init() {
    try {
        const isLocal = window.location.protocol === 'file:' || window.location.hostname === 'localhost';

        // Setup Telegram WebApp
        let initData = "";
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.expand();
            window.Telegram.WebApp.ready();
            initData = window.Telegram.WebApp.initData || (isLocal ? "mock_init_data" : "");
        } else if (isLocal) {
            initData = "mock_init_data";
        }

        if (!initData) {
            showToast("Ошибка: нет данных инициализации Telegram");
            return;
        }

        // Initialize Realm
        app = new Realm.App({ id: APP_ID });

        if (isLocal) {
            // Mock Login
            currentUser = {
                functions: {
                    auth: async () => "123456789",
                    getProfile: async () => ({
                        id: "123456789",
                        balance: 100,
                        subscription_end: new Date(Date.now() + 86400000 * 5),
                        referrals_count: 2,
                        used_configs: [
                            { config_name: "Mock Config 1", period: "1_month", config_link: "vless://mock" }
                        ]
                    }),
                    getConfigs: async () => ({
                        '1_month': { price: 50, days: 30, name: "1 месяц" },
                        '2_months': { price: 90, days: 60, name: "2 месяца" }
                    }),
                    buySubscription: async (period) => ({ success: true, new_balance: 50 }),
                    createPayment: async (amount) => ({ confirmation_url: "https://example.com/pay" })
                }
            };
            await loadData();
        } else {
            // Real Login
            // Use an anonymous credential or custom function auth.
            // Assuming Custom Function Auth is configured to accept initData
            const credentials = Realm.Credentials.function({ initData });
            currentUser = await app.logIn(credentials);
            await loadData();
        }

        // Hide loader, show app
        loaderDiv.classList.add('hidden');
        appDiv.classList.remove('hidden');

        setupEventListeners();

    } catch (error) {
        console.error("Initialization error:", error);
        showToast("Ошибка загрузки: " + error.message);
        loaderDiv.innerHTML = `<p class="text-red-500">Ошибка: ${error.message}</p>`;
    }
}

// Load User Data
async function loadData() {
    try {
        // Fetch profile
        userProfile = await currentUser.functions.getProfile();
        updateProfileUI();

        // Fetch configs
        subscriptionConfigs = await currentUser.functions.getConfigs();
        renderSubscriptionOptions();
        renderConfigsList();

    } catch (error) {
        console.error("Failed to load data", error);
        showToast("Не удалось загрузить данные");
    }
}

// Update UI with Profile Data
function updateProfileUI() {
    balanceEl.textContent = `${userProfile.balance} ₽`;
    refEl.textContent = userProfile.referrals_count;

    if (userProfile.subscription_end) {
        const endDate = new Date(userProfile.subscription_end);
        const now = new Date();
        if (endDate > now) {
            const daysLeft = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));
            subEl.textContent = `${daysLeft} дней (до ${endDate.toLocaleDateString()})`;
            subEl.classList.add('text-green-600');
        } else {
            subEl.textContent = "Истекла";
            subEl.classList.add('text-red-500');
        }
    } else {
        subEl.textContent = "Нет активной";
        subEl.classList.add('text-gray-500');
    }
}

// Render User's Purchased Configs
function renderConfigsList() {
    configsListEl.innerHTML = "";
    if (!userProfile.used_configs || userProfile.used_configs.length === 0) {
        configsListEl.innerHTML = `<p class="text-gray-500 text-sm py-4">У вас пока нет конфигов. Перейдите в "Купить VPN".</p>`;
        return;
    }

    userProfile.used_configs.forEach((config, index) => {
        const div = document.createElement('div');
        div.className = "p-3 border rounded-lg bg-gray-50 shadow-sm";
        div.innerHTML = `
            <div class="font-semibold text-sm mb-1">${config.config_name}</div>
            <div class="text-xs text-gray-500 mb-2">Период: ${config.period}</div>
            <div class="flex">
                <input type="text" readonly value="${config.config_link}" class="text-xs p-1 border rounded flex-grow mr-2 bg-white" id="link-${index}">
                <button class="bg-blue-500 text-white px-2 py-1 rounded text-xs hover:bg-blue-600" onclick="copyLink('link-${index}')">Копировать</button>
            </div>
        `;
        configsListEl.appendChild(div);
    });
}

// Render Subscription Options for Purchase
function renderSubscriptionOptions() {
    subOptionsEl.innerHTML = "";
    Object.keys(subscriptionConfigs).forEach(period => {
        const conf = subscriptionConfigs[period];
        const div = document.createElement('div');
        div.className = "flex justify-between items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer transition";
        div.innerHTML = `
            <div>
                <div class="font-semibold">${conf.name || (conf.days + ' дней')}</div>
                <div class="text-sm text-gray-500">${conf.price} ₽</div>
            </div>
            <button class="bg-blue-500 text-white px-3 py-1 rounded-lg text-sm hover:bg-blue-600" onclick="buySubscription('${period}', ${conf.price})">
                Купить
            </button>
        `;
        subOptionsEl.appendChild(div);
    });
}

// Event Listeners Setup
function setupEventListeners() {
    // Navigation
    btnTopup.addEventListener('click', () => switchView('topup'));
    btnBuy.addEventListener('click', () => switchView('buy'));
    btnBackBuy.addEventListener('click', () => switchView('home'));
    btnBackTopup.addEventListener('click', () => switchView('home'));

    // Topup Logic
    document.querySelectorAll('.topup-preset').forEach(btn => {
        btn.addEventListener('click', (e) => {
            topupAmount.value = e.target.dataset.amount;
        });
    });

    btnPay.addEventListener('click', async () => {
        const amount = parseInt(topupAmount.value);
        if (isNaN(amount) || amount < 50) {
            showToast("Минимальная сумма 50 ₽");
            return;
        }

        btnPay.disabled = true;
        btnPay.innerText = "Создание платежа...";

        try {
            const res = await currentUser.functions.createPayment(amount);
            if (res.confirmation_url) {
                if (window.Telegram && window.Telegram.WebApp) {
                    window.Telegram.WebApp.openLink(res.confirmation_url);
                } else {
                    window.open(res.confirmation_url, '_blank');
                }
                showToast("Ожидание оплаты...");
                // Note: Real app needs polling checkPayment here or webhook listener
            } else {
                showToast("Ошибка создания платежа");
            }
        } catch (error) {
            console.error(error);
            showToast("Ошибка: " + error.message);
        } finally {
            btnPay.disabled = false;
            btnPay.innerText = "Оплатить";
        }
    });
}

// Buy Subscription Logic
window.buySubscription = async function(period, price) {
    if (userProfile.balance < price) {
        showToast("Недостаточно средств. Пополните баланс.");
        switchView('topup');
        return;
    }

    if (confirm(`Подтверждаете покупку за ${price} ₽?`)) {
        try {
            showToast("Покупка...");
            const res = await currentUser.functions.buySubscription(period);
            if (res.success) {
                showToast("Подписка успешно куплена!");
                await loadData(); // reload profile and configs
                switchView('home');
            }
        } catch (error) {
            console.error(error);
            showToast("Ошибка: " + error.message);
        }
    }
};

// Utils
function switchView(viewName) {
    viewHome.classList.add('hidden');
    viewBuy.classList.add('hidden');
    viewTopup.classList.add('hidden');

    if (viewName === 'home') viewHome.classList.remove('hidden');
    if (viewName === 'buy') viewBuy.classList.remove('hidden');
    if (viewName === 'topup') viewTopup.classList.remove('hidden');
}

window.copyLink = function(inputId) {
    const input = document.getElementById(inputId);
    input.select();
    input.setSelectionRange(0, 99999); // For mobile devices
    navigator.clipboard.writeText(input.value)
        .then(() => showToast("Ссылка скопирована!"))
        .catch(() => showToast("Ошибка копирования"));
};

function showToast(message) {
    toastMsg.textContent = message;
    toastEl.classList.remove('hidden');
    toastEl.style.opacity = '1';

    setTimeout(() => {
        toastEl.style.opacity = '0';
        setTimeout(() => toastEl.classList.add('hidden'), 300);
    }, 3000);
}

// Start app
document.addEventListener('DOMContentLoaded', init);