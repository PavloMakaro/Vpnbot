// app.js

const tg = window.Telegram.WebApp;
const APP_ID = "YOUR_REALM_APP_ID"; // **IMPORTANT: Replace with actual Atlas App ID**
const app = new Realm.App({ id: APP_ID });
let currentUser = null;
let currentConfigs = {};

// Initialize Telegram WebApp
tg.expand();
tg.ready();
tg.MainButton.hide();

document.addEventListener('DOMContentLoaded', async () => {
    try {
        await authenticate();
        await loadProfile();
        await loadConfigs();
        showProfileView();
    } catch (error) {
        console.error("Initialization error:", error);
        tg.showAlert(`Ошибка инициализации: ${error.message}`);
    }
});

// Authentication using Custom JWT/Function Provider
async function authenticate() {
    const initData = tg.initData;
    if (!initData) {
        throw new Error("Не удалось получить данные авторизации Telegram.");
    }

    // We use the start_param for referral logic
    const start_param = tg.initDataUnsafe?.start_param || null;

    // Create credentials for custom function auth
    const credentials = Realm.Credentials.function({ initData: initData, start_param: start_param });

    currentUser = await app.logIn(credentials);
    console.log("Authenticated successfully as user:", currentUser.id);
}

// Load User Profile Data
async function loadProfile() {
    if (!currentUser) return;

    try {
        const profile = await currentUser.functions.getProfile();

        // Update UI
        document.getElementById('userName').innerText = profile.first_name || 'Пользователь';
        document.getElementById('userUsername').innerText = profile.username ? `@${profile.username}` : '';
        document.getElementById('userBalance').innerText = `${profile.balance} ₽`;
        document.getElementById('buyViewBalance').innerText = `${profile.balance} ₽`;
        document.getElementById('userReferrals').innerText = profile.referrals_count;

        const subBadge = document.getElementById('subStatusBadge');
        const subDate = document.getElementById('subEndDate');

        if (profile.daysLeft > 0) {
            subBadge.innerText = 'Активна';
            subBadge.className = 'px-2 py-1 rounded text-xs font-bold bg-green-100 text-green-600';
            subDate.innerText = `До ${profile.subscriptionEndDateFormatted} (осталось ${profile.daysLeft} дн.)`;
        } else {
            subBadge.innerText = 'Неактивна';
            subBadge.className = 'px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-600';
            subDate.innerText = 'Нет активной подписки';
        }

        // Render Used Configs
        const configsList = document.getElementById('configsList');
        document.getElementById('configsCount').innerText = profile.used_configs.length;
        configsList.innerHTML = '';

        if (profile.used_configs.length === 0) {
            configsList.innerHTML = '<p class="tg-hint text-sm text-center py-4">Нет выданных конфигов</p>';
        } else {
            profile.used_configs.forEach(conf => {
                const el = document.createElement('div');
                el.className = 'tg-secondary-bg p-3 rounded-xl shadow-sm text-sm break-all relative group cursor-pointer hover:bg-opacity-80 transition';
                el.innerHTML = `
                    <p class="font-bold mb-1" style="color: var(--tg-theme-button-color, #2481cc);">${conf.config_name}</p>
                    <p class="tg-hint text-xs mb-2">Выдан: ${conf.issue_date}</p>
                    <code class="block bg-black bg-opacity-10 p-2 rounded">${conf.config_link}</code>
                    <div class="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition rounded-xl">
                        <span class="text-white font-bold">Нажмите, чтобы скопировать</span>
                    </div>
                `;
                el.onclick = () => {
                    navigator.clipboard.writeText(conf.config_link).then(() => {
                        tg.showPopup({ title: "Успешно", message: "Ссылка скопирована в буфер обмена!" });
                    });
                };
                configsList.appendChild(el);
            });
        }

    } catch (err) {
        console.error("Failed to load profile", err);
        tg.showAlert("Не удалось загрузить профиль.");
    }
}

// Load Subscription Config Options
async function loadConfigs() {
    if (!currentUser) return;
    try {
        currentConfigs = await currentUser.functions.getConfigs();
        const container = document.getElementById('subscriptionOptions');
        container.innerHTML = '';

        for (const [key, details] of Object.entries(currentConfigs)) {
            const btn = document.createElement('button');
            btn.className = 'w-full tg-secondary-bg rounded-xl py-4 px-5 font-semibold flex justify-between items-center shadow-sm hover:opacity-90 transition';
            btn.innerHTML = `
                <span>${details.days} дней</span>
                <span style="color: var(--tg-theme-button-color, #2481cc);">${details.price} ₽</span>
            `;
            btn.onclick = () => buySubscription(key, details.price, details.days);
            container.appendChild(btn);
        }
    } catch (err) {
        console.error("Failed to load configs", err);
    }
}

// Purchase Subscription Logic
async function buySubscription(periodKey, price, days) {
    tg.showConfirm(`Купить подписку на ${days} дней за ${price} ₽?`, async (confirmed) => {
        if (!confirmed) return;

        try {
            tg.showPopup({ title: "Обработка", message: "Покупка подписки..." });
            const result = await currentUser.functions.buySubscription(periodKey);

            if (result.success) {
                tg.showAlert(result.message);
                await loadProfile(); // Reload data
                showProfileView();
            } else {
                tg.showAlert(`Ошибка: ${result.message}`);
                if (result.message.includes("Недостаточно средств")) {
                    showTopUpView();
                }
            }
        } catch (err) {
            console.error("Buy error:", err);
            tg.showAlert("Произошла ошибка при покупке подписки.");
        }
    });
}

// Top Up Logic
function setTopUpAmount(amount) {
    document.getElementById('customAmount').value = amount;
    checkCustomAmount();
}

function checkCustomAmount() {
    const amount = parseInt(document.getElementById('customAmount').value);
    const btn = document.getElementById('payButton');

    if (amount >= 50 && amount <= 50000) {
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
    } else {
        btn.disabled = true;
        btn.classList.add('opacity-50', 'cursor-not-allowed');
    }
}

async function processTopUp() {
    const amount = parseInt(document.getElementById('customAmount').value);
    if (!amount || amount < 50) return;

    try {
        const btn = document.getElementById('payButton');
        btn.innerText = "Создание платежа...";
        btn.disabled = true;

        const result = await currentUser.functions.createPayment(amount);

        // Open confirmation URL in external browser/telegram
        tg.openLink(result.confirmation_url);

        // We set up a polling mechanism to check payment status
        pollPaymentStatus(result.payment_id);

    } catch (err) {
        console.error("Payment error:", err);
        tg.showAlert("Ошибка при создании платежа. Попробуйте позже.");
        document.getElementById('payButton').innerText = "Оплатить";
        checkCustomAmount();
    }
}

// Poll payment status
let pollInterval;
async function pollPaymentStatus(paymentId) {
    tg.showPopup({ title: "Ожидание", message: "Ожидаем подтверждения платежа..." });
    let attempts = 0;

    pollInterval = setInterval(async () => {
        attempts++;
        if (attempts > 60) { // 10 minutes max polling (10s interval)
            clearInterval(pollInterval);
            document.getElementById('payButton').innerText = "Оплатить";
            return;
        }

        try {
            const checkResult = await currentUser.functions.checkPayment(paymentId);
            if (checkResult.status === 'succeeded') {
                clearInterval(pollInterval);
                tg.showAlert(checkResult.message);
                await loadProfile();
                showProfileView();
            } else if (checkResult.status === 'canceled') {
                clearInterval(pollInterval);
                tg.showAlert("Платеж отменен.");
                document.getElementById('payButton').innerText = "Оплатить";
            }
            // If pending, keep polling
        } catch (err) {
            console.error("Poll error:", err);
        }
    }, 10000); // Check every 10 seconds
}


// Navigation
function hideAllViews() {
    document.getElementById('loading').classList.remove('active');
    document.getElementById('loading').style.display = 'none';
    document.getElementById('profileView').classList.remove('active');
    document.getElementById('topUpView').classList.remove('active');
    document.getElementById('buyView').classList.remove('active');
}

function showProfileView() {
    hideAllViews();
    document.getElementById('profileView').classList.add('active');
    tg.BackButton.hide();
}

function showTopUpView() {
    hideAllViews();
    document.getElementById('topUpView').classList.add('active');
    document.getElementById('customAmount').value = '';
    checkCustomAmount();
    tg.BackButton.show();
    tg.BackButton.onClick(showProfileView);
}

function showBuyView() {
    hideAllViews();
    document.getElementById('buyView').classList.add('active');
    tg.BackButton.show();
    tg.BackButton.onClick(showProfileView);
}