// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();
tg.enableClosingConfirmation();

// Initialize Realm App (Stitch)
// REPLACE THIS WITH YOUR ACTUAL APP ID
const APP_ID = "vpn-bot-app-id";
const app = new Realm.App({ id: APP_ID });

// State
let currentUser = null;
let userProfile = null;

// DOM Elements
const loadingScreen = document.getElementById('loading-screen');
const userNameEl = document.getElementById('user-name');
const userIdEl = document.getElementById('user-id');
const userAvatarTextEl = document.getElementById('user-avatar-text');
const userBalanceEl = document.getElementById('user-balance');
const subStatusBanner = document.getElementById('sub-status-banner');
const subDaysLeftEl = document.getElementById('sub-days-left');
const plansContainer = document.getElementById('plans-container');
const configsContainer = document.getElementById('configs-container');
const topupBtn = document.getElementById('topup-btn');
const customAmountInput = document.getElementById('custom-amount');
const amountBtns = document.querySelectorAll('.amount-btn');
const toastEl = document.getElementById('toast');
const toastMessageEl = document.getElementById('toast-message');
const toastIconEl = document.getElementById('toast-icon');

// Utils
function showToast(message, type = 'info') {
    toastMessageEl.textContent = message;
    toastEl.className = `fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-xl border transition-opacity duration-300 z-50 flex items-center ${type === 'success' ? 'border-green-500' : type === 'error' ? 'border-red-500' : 'border-gray-700'}`;

    if (type === 'success') {
        toastIconEl.className = 'fas fa-check-circle text-green-500 mr-2';
    } else if (type === 'error') {
        toastIconEl.className = 'fas fa-exclamation-circle text-red-500 mr-2';
    } else {
        toastIconEl.className = 'fas fa-info-circle text-blue-500 mr-2';
    }

    toastEl.style.opacity = '1';
    setTimeout(() => {
        toastEl.style.opacity = '0';
    }, 3000);
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

// Auth
async function login() {
    try {
        const initData = tg.initData;
        if (!initData) {
            // For testing in browser without Telegram
            console.warn("No initData found. Running in demo mode?");
            // return;
        }

        // Authenticate using Custom Function
        const credentials = Realm.Credentials.function({ initData: initData });
        currentUser = await app.logIn(credentials);
        console.log("Logged in as:", currentUser.id);

        await loadData();
    } catch (err) {
        console.error("Failed to log in", err);
        showToast("Ошибка авторизации: " + err.message, 'error');
        loadingScreen.innerHTML = `<div class="text-center p-4"><p class="text-red-500 mb-2">Ошибка авторизации</p><button onclick="location.reload()" class="bg-blue-600 px-4 py-2 rounded">Повторить</button></div>`;
    }
}

// Data Loading
async function loadData() {
    try {
        // Fetch User Profile
        userProfile = await currentUser.functions.getProfile();
        renderProfile(userProfile);

        // Fetch Plans
        const plans = await currentUser.functions.getPlans();
        renderPlans(plans);

        // Fetch Configs
        const configs = await currentUser.functions.getMyConfigs();
        renderConfigs(configs);

        loadingScreen.style.display = 'none';
    } catch (err) {
        console.error("Failed to load data", err);
        showToast("Ошибка загрузки данных", 'error');
    }
}

// Rendering
function renderProfile(profile) {
    if (!profile) return;

    userNameEl.textContent = profile.first_name || 'User';
    userIdEl.textContent = profile.user_id;
    userAvatarTextEl.textContent = (profile.first_name || 'U')[0].toUpperCase();
    userBalanceEl.textContent = profile.balance;

    if (profile.days_left > 0) {
        subStatusBanner.classList.remove('hidden');
        subDaysLeftEl.textContent = `${profile.days_left} дней`;
    } else {
        subStatusBanner.classList.add('hidden');
    }
}

function renderPlans(plans) {
    plansContainer.innerHTML = '';
    if (!plans || Object.keys(plans).length === 0) {
        plansContainer.innerHTML = '<p class="text-gray-500 text-center">Нет доступных планов</p>';
        return;
    }

    for (const [key, plan] of Object.entries(plans)) {
        const card = document.createElement('div');
        card.className = 'plan-card p-4 rounded-xl flex justify-between items-center cursor-pointer';
        card.innerHTML = `
            <div>
                <h3 class="font-bold text-lg text-white">${plan.days} дней</h3>
                <p class="text-gray-400 text-sm">VPN подписка</p>
            </div>
            <div class="flex items-center">
                <span class="font-bold text-xl mr-3 text-blue-400">${plan.price} ₽</span>
                <button class="bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-3 py-1.5 text-sm font-bold transition">
                    Купить
                </button>
            </div>
        `;
        card.onclick = () => buySubscription(key, plan);
        plansContainer.appendChild(card);
    }
}

function renderConfigs(configs) {
    configsContainer.innerHTML = '';
    if (!configs || configs.length === 0) {
        configsContainer.innerHTML = '<p class="text-gray-500 text-center py-4">У вас пока нет конфигов</p>';
        return;
    }

    configs.forEach(conf => {
        const card = document.createElement('div');
        card.className = 'config-card p-4 rounded-xl shadow-md';
        card.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <h3 class="font-bold text-white truncate pr-2">${conf.config_name}</h3>
                <span class="text-xs bg-gray-700 px-2 py-1 rounded text-gray-300">${conf.period}</span>
            </div>
            <p class="text-xs text-gray-400 mb-3">Выдан: ${conf.issue_date}</p>
            <div class="bg-gray-900 rounded p-2 mb-3 relative group">
                <code class="text-xs text-green-400 break-all line-clamp-2">${conf.config_link}</code>
                <button class="copy-btn absolute top-1 right-1 bg-gray-700 hover:bg-gray-600 text-white p-1 rounded text-xs" data-copy="${conf.config_link}">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
            <button class="w-full bg-gray-700 hover:bg-gray-600 text-sm py-2 rounded text-gray-300 transition" onclick="showInstructions()">
                <i class="fas fa-book mr-1"></i> Инструкция
            </button>
        `;
        configsContainer.appendChild(card);
    });

    // Add event listeners for copy buttons
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const text = btn.getAttribute('data-copy');
            navigator.clipboard.writeText(text).then(() => {
                showToast("Скопировано в буфер!", 'success');
            });
        });
    });
}

function showInstructions() {
    tg.showPopup({
        title: "Инструкция",
        message: "Скачайте V2RayNG (Android) или V2Box (iOS), скопируйте ссылку и импортируйте её из буфера обмена.",
        buttons: [{type: "ok"}]
    });
}

// Actions
async function buySubscription(planKey, plan) {
    tg.showConfirm(`Купить подписку на ${plan.days} дней за ${plan.price} ₽?`, async (confirmed) => {
        if (confirmed) {
            try {
                loadingScreen.style.display = 'flex';
                const result = await currentUser.functions.buySubscription(planKey);

                if (result.success) {
                    showToast("Подписка успешно куплена!", 'success');
                    await loadData(); // Reload data
                } else {
                    showToast(result.error || "Ошибка покупки", 'error');
                }
            } catch (err) {
                console.error("Buy error", err);
                showToast("Ошибка при покупке: " + err.message, 'error');
            } finally {
                loadingScreen.style.display = 'none';
            }
        }
    });
}

async function handleTopUp() {
    let amount = parseInt(customAmountInput.value);
    if (!amount || amount < 50) {
        showToast("Минимальная сумма 50 ₽", 'error');
        return;
    }

    try {
        loadingScreen.style.display = 'flex';
        const result = await currentUser.functions.createPayment(amount);

        if (result && result.confirmation_url) {
            tg.openLink(result.confirmation_url);
            showToast("Открыта страница оплаты. После оплаты обновите приложение.", 'info');
        } else {
            showToast("Ошибка создания платежа", 'error');
        }
    } catch (err) {
        console.error("TopUp error", err);
        showToast("Ошибка: " + err.message, 'error');
    } finally {
        loadingScreen.style.display = 'none';
    }
}

// Event Listeners
amountBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        customAmountInput.value = btn.getAttribute('data-amount');
    });
});

topupBtn.addEventListener('click', handleTopUp);

// Init
window.addEventListener('load', () => {
    // If running in telegram, initData is available
    if (tg.initData) {
        login();
    } else {
        // Demo mode or error
        console.log("No initData. Waiting...");
        // You might want to uncomment this for local testing with mock data if needed
        // login();
    }
});
