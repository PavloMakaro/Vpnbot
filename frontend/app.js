const APP_ID = "vnp-bot-app-id"; // ЗАМЕНИТЕ НА ВАШ APP ID
const app = new Realm.App({ id: APP_ID });
let currentUser = null;

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// UI Elements
const loadingEl = document.getElementById('loading');
const balanceEl = document.getElementById('balance');
const userNameEl = document.getElementById('user-name');
const profileNameEl = document.getElementById('profile-name');
const profileUsernameEl = document.getElementById('profile-username');
const profileBalanceEl = document.getElementById('profile-balance');
const profileSubEl = document.getElementById('profile-sub');
const refLinkEl = document.getElementById('ref-link');
const refCountEl = document.getElementById('ref-count');
const configsListEl = document.getElementById('configs-list');

// Main Init
async function init() {
    try {
        if (!app.currentUser) {
            // Login using Custom Function Auth (validating initData)
            const credentials = Realm.Credentials.function({
                initData: tg.initData
            });
            currentUser = await app.logIn(credentials);
        } else {
            currentUser = app.currentUser;
        }

        await loadUserData();
        loadingEl.classList.add('hidden');

    } catch (err) {
        console.error("Failed to login", err);
        alert("Authentication failed: " + err.message);
    }
}

async function loadUserData() {
    if (!currentUser) return;
    try {
        const userData = await currentUser.callFunction("getUser");
        updateUI(userData);
    } catch (err) {
        console.error("Error loading user data:", err);
    }
}

function updateUI(data) {
    if (!data) return;

    // Balance
    balanceEl.textContent = `${data.balance} ₽`;
    profileBalanceEl.textContent = `${data.balance} ₽`;

    // Names
    userNameEl.textContent = data.first_name;
    profileNameEl.textContent = data.first_name;
    profileUsernameEl.textContent = `@${data.username}`;

    // Subscription
    if (data.subscription_end) {
        const endDate = new Date(data.subscription_end);
        const now = new Date();
        if (endDate > now) {
            const diffTime = Math.abs(endDate - now);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            profileSubEl.textContent = `Активна (${diffDays} дн.)`;
            profileSubEl.classList.remove('text-red-500');
            profileSubEl.classList.add('text-green-400');
        } else {
            profileSubEl.textContent = "Истекла";
            profileSubEl.classList.add('text-red-500');
            profileSubEl.classList.remove('text-green-400');
        }
    } else {
        profileSubEl.textContent = "Нет активной";
        profileSubEl.classList.add('text-red-500');
        profileSubEl.classList.remove('text-green-400');
    }

    // Referral
    refLinkEl.textContent = `https://t.me/vpni50_bot?start=${currentUser.id}`; // Update bot username
    refCountEl.textContent = data.referrals_count || 0;
}

// Tabs Logic
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));

    document.getElementById(`tab-${tabId}`).classList.add('active');
    document.getElementById(`tab-${tabId}`).classList.remove('hidden');

    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active', 'text-blue-400'));
    document.querySelector(`[onclick="switchTab('${tabId}')"]`).classList.add('active', 'text-blue-400');

    if (tabId === 'configs') {
        loadConfigs();
    }
}

// Configs
async function loadConfigs() {
    configsListEl.innerHTML = '<p class="text-gray-400 text-center py-8">Загрузка...</p>';
    try {
        const configs = await currentUser.callFunction("getConfigs");
        renderConfigs(configs);
    } catch (err) {
        configsListEl.innerHTML = '<p class="text-red-400 text-center py-8">Ошибка загрузки</p>';
    }
}

function renderConfigs(configs) {
    if (!configs || configs.length === 0) {
        configsListEl.innerHTML = '<p class="text-gray-400 text-center py-8">Нет активных конфигов</p>';
        return;
    }

    configsListEl.innerHTML = configs.map(conf => `
        <div class="bg-gray-800 p-4 rounded-lg border border-gray-700">
            <div class="flex justify-between items-start mb-2">
                <div>
                    <h3 class="font-bold text-sm">${conf.config_name}</h3>
                    <p class="text-xs text-gray-500">${conf.period} дней • Выдан: ${new Date(conf.issue_date).toLocaleDateString()}</p>
                </div>
                <button onclick="copyToClipboard('${conf.config_link}')" class="text-blue-400 text-xs bg-gray-900 px-2 py-1 rounded hover:bg-gray-700">Копировать</button>
            </div>
            <code class="block bg-black/30 p-2 rounded text-[10px] text-gray-400 break-all truncate font-mono">${conf.config_link}</code>
        </div>
    `).join('');
}

// Actions
async function buySubscription(period) {
    if (!confirm(`Купить подписку на ${period.replace('_', ' ')}?`)) return;

    tg.MainButton.showProgress();
    try {
        const result = await currentUser.callFunction("buySubscription", { period });
        if (result.success) {
            alert("Успешно! Ваш конфиг в разделе 'Мои конфиги'.");
            loadUserData();
            switchTab('configs');
        } else {
            alert("Ошибка: " + result.message);
        }
    } catch (err) {
        alert("Ошибка покупки: " + err.message);
    } finally {
        tg.MainButton.hideProgress();
    }
}

// Topup Modal
function openTopupModal() {
    const modal = document.getElementById('modal-topup');
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        modal.querySelector('div').classList.remove('scale-95');
        modal.querySelector('div').classList.add('scale-100');
    }, 10);
}

function closeModal(id) {
    const modal = document.getElementById(id);
    modal.classList.add('opacity-0');
    modal.querySelector('div').classList.remove('scale-100');
    modal.querySelector('div').classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

function setTopupAmount(amount) {
    document.getElementById('topup-amount').value = amount;
}

async function submitTopup() {
    const amount = document.getElementById('topup-amount').value;
    if (!amount || amount < 50) {
        alert("Минимум 50 рублей");
        return;
    }

    closeModal('modal-topup');
    tg.MainButton.setText(`Оплатить ${amount} ₽`);
    tg.MainButton.show();
    tg.MainButton.onClick(async () => {
        tg.MainButton.showProgress();
        try {
            const result = await currentUser.callFunction("topupBalance", { amount: parseInt(amount) });
            if (result.payment_url) {
                tg.openLink(result.payment_url);
            } else {
                alert("Ошибка создания платежа");
            }
        } catch (err) {
            alert("Ошибка: " + err.message);
        } finally {
            tg.MainButton.hideProgress();
            tg.MainButton.hide();
        }
    });
}

// Utils
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        tg.showPopup({ message: 'Ссылка скопирована!' });
    });
}

function copyRefLink() {
    copyToClipboard(refLinkEl.textContent);
}

function openSupport() {
    tg.openTelegramLink("https://t.me/Gl1ch555");
}

// Start
init();
