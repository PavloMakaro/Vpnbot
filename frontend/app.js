const tg = window.Telegram.WebApp;
tg.expand();

// Fallback logic for local testing without Telegram
const mockInitData = new URLSearchParams({
    query_id: "AAHdF6kqAAAAAN0XqSpVxxx",
    user: JSON.stringify({
        id: 123456789,
        first_name: "Test",
        last_name: "User",
        username: "testuser",
        language_code: "ru",
        allows_write_to_pm: true
    }),
    auth_date: "1672531200",
    hash: "mockhash"
}).toString();

const initData = tg.initData || mockInitData;

const REALM_APP_ID = "vpn_bot_app-xxxxx"; // Replace with real ID during deployment

let realmApp;
let currentUserProfile = null;
let subscriptionConfigs = null;

// UI Elements
const loadingScreen = document.getElementById('loading');
const appScreen = document.getElementById('app');
const errorScreen = document.getElementById('error-screen');
const notifications = document.getElementById('notifications');

async function init() {
    try {
        if (!initData && !window.Telegram.WebApp.initDataUnsafe?.user) {
            throw new Error("No Telegram Init Data");
        }

        // Setup Realm
        realmApp = new Realm.App({ id: REALM_APP_ID });

        // Custom Function Auth
        const credentials = Realm.Credentials.function({ initData });
        await realmApp.logIn(credentials);

        // Fetch Profile
        await loadProfile();

        // Fetch Subscriptions Configuration
        await loadConfigOptions();

        // Check for pending payments (replacing query params)
        await checkPendingPayments();

        // Show App
        loadingScreen.classList.add('hidden');
        appScreen.classList.remove('hidden');

    } catch (err) {
        console.error("Initialization error:", err);
        loadingScreen.classList.add('hidden');
        errorScreen.classList.remove('hidden');
        document.getElementById('error-message').textContent = err.message || "Ошибка подключения к серверу.";
    }
}

async function loadProfile() {
    try {
        currentUserProfile = await realmApp.currentUser.functions.getProfile();
        updateProfileUI();
    } catch (err) {
        console.error("Error loading profile:", err);
        showNotification("Ошибка загрузки профиля", "error");
    }
}

function updateProfileUI() {
    if (!currentUserProfile) return;

    document.getElementById('user-greeting').textContent = `Привет, ${currentUserProfile.first_name || 'пользователь'}!`;
    document.getElementById('user-balance').textContent = `${currentUserProfile.balance || 0} ₽`;

    const statusEl = document.getElementById('sub-status');
    const subEnd = currentUserProfile.subscription_end;

    if (!subEnd) {
        statusEl.textContent = "Нет активной подписки";
        statusEl.className = "text-sm text-red-500";
    } else {
        const endDate = new Date(subEnd.replace(' ', 'T'));
        const now = new Date();

        if (endDate > now) {
            const diffDays = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));
            statusEl.textContent = `Активна еще ${diffDays} дней (до ${endDate.toLocaleDateString('ru-RU')})`;
            statusEl.className = "text-sm text-green-500";
        } else {
            statusEl.textContent = "Подписка истекла";
            statusEl.className = "text-sm text-red-500";
        }
    }

    renderUsedConfigs();
}

async function loadConfigOptions() {
    try {
        subscriptionConfigs = await realmApp.currentUser.functions.getConfigs();
        renderPlans();
    } catch (err) {
        console.error("Error loading configs:", err);
    }
}

function renderPlans() {
    const container = document.getElementById('plans-container');
    container.innerHTML = '';

    if (!subscriptionConfigs) return;

    Object.keys(subscriptionConfigs).forEach(periodKey => {
        const plan = subscriptionConfigs[periodKey];
        const el = document.createElement('div');
        el.className = "tg-card flex justify-between items-center";

        const info = document.createElement('div');
        info.innerHTML = `
            <div class="font-bold">${plan.title}</div>
            <div class="text-sm tg-text-hint">${plan.price} ₽</div>
        `;

        const btn = document.createElement('button');
        btn.className = "tg-button text-sm px-4 py-2";
        btn.textContent = "Купить";
        btn.onclick = () => buySubscription(periodKey, plan.price);

        el.appendChild(info);
        el.appendChild(btn);
        container.appendChild(el);
    });
}

function renderUsedConfigs() {
    const container = document.getElementById('configs-container');
    const noConfigs = document.getElementById('no-configs');
    container.innerHTML = '';

    const usedConfigs = currentUserProfile?.used_configs || [];

    if (usedConfigs.length === 0) {
        noConfigs.classList.remove('hidden');
        return;
    }

    noConfigs.classList.add('hidden');

    // Sort by issue date descending
    usedConfigs.sort((a, b) => new Date(b.issue_date.replace(' ', 'T')) - new Date(a.issue_date.replace(' ', 'T')));

    usedConfigs.forEach(conf => {
        const el = document.createElement('div');
        el.className = "tg-card";

        const periodTitle = subscriptionConfigs ?
            (subscriptionConfigs[conf.period]?.title || conf.period) : conf.period;

        const dateObj = new Date(conf.issue_date.replace(' ', 'T'));
        const dateStr = dateObj.toLocaleDateString('ru-RU');

        el.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <div class="font-bold text-sm truncate pr-2">${conf.config_name}</div>
                <div class="text-xs tg-text-hint whitespace-nowrap">${dateStr}</div>
            </div>
            <div class="text-xs tg-text-hint mb-3">Период: ${periodTitle}</div>
            <button onclick="openConfigModal('${conf.config_link}')" class="w-full text-center text-sm tg-link font-medium py-1">Показать ссылку</button>
        `;

        container.appendChild(el);
    });
}

async function buySubscription(period, price) {
    if ((currentUserProfile.balance || 0) < price) {
        showNotification("Недостаточно средств. Пополните баланс.", "error");
        tg.HapticFeedback.notificationOccurred("error");
        // Scroll to topup
        document.getElementById('topup-amount').focus();
        return;
    }

    tg.HapticFeedback.impactOccurred("medium");
    showLoading(true);

    try {
        const result = await realmApp.currentUser.functions.buySubscription(period);
        if (result.success) {
            tg.HapticFeedback.notificationOccurred("success");
            showNotification(result.message, "success");
            await loadProfile(); // Refresh profile

            // Show new config modal
            if (result.config && result.config.link) {
                setTimeout(() => openConfigModal(result.config.link), 500);
            }
        } else {
            tg.HapticFeedback.notificationOccurred("error");
            showNotification(result.error || "Ошибка при покупке", "error");
        }
    } catch (err) {
        console.error(err);
        showNotification("Произошла ошибка связи с сервером.", "error");
    } finally {
        showLoading(false);
    }
}

// Topup Logic
document.getElementById('btn-topup').addEventListener('click', async () => {
    const amountInput = document.getElementById('topup-amount');
    const amount = parseInt(amountInput.value);

    if (isNaN(amount) || amount < 50) {
        showNotification("Минимальная сумма пополнения 50 ₽", "error");
        return;
    }

    tg.HapticFeedback.impactOccurred("light");
    const btn = document.getElementById('btn-topup');
    btn.disabled = true;
    btn.textContent = "...";

    try {
        const result = await realmApp.currentUser.functions.createPayment(amount);
        if (result.success && result.confirmation_url) {
            // Open payment link
            tg.openLink(result.confirmation_url);

            // Note: In Telegram WebApp, we don't rely on return URLs modifying query params reliably.
            // When the user returns, we should trigger a check.
            showNotification("Ожидание оплаты...", "info");

            // Start polling for this specific payment
            pollPaymentStatus(result.payment_id);

        } else {
            showNotification(result.error || "Ошибка создания платежа", "error");
        }
    } catch (err) {
        console.error(err);
        showNotification("Ошибка связи с сервером", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Оплатить";
        amountInput.value = '';
    }
});

async function pollPaymentStatus(paymentId, attempts = 0) {
    if (attempts > 30) { // Give up after ~5 mins (10s intervals)
        showNotification("Время ожидания оплаты истекло.", "info");
        return;
    }

    try {
        const result = await realmApp.currentUser.functions.checkPayment(paymentId);

        if (result.success && result.status === 'succeeded') {
            tg.HapticFeedback.notificationOccurred("success");
            showNotification(`Баланс пополнен на ${result.amount} ₽!`, "success");
            await loadProfile();
            return;
        } else if (result.success && result.status === 'canceled') {
            showNotification("Платеж отменен.", "error");
            return;
        }

    } catch (err) {
        console.error("Polling error", err);
    }

    // Continue polling
    setTimeout(() => pollPaymentStatus(paymentId, attempts + 1), 10000);
}

// General pending payments check on load
async function checkPendingPayments() {
    try {
        const result = await realmApp.currentUser.functions.checkPendingPayments();
        if (result.success && result.updated > 0) {
            tg.HapticFeedback.notificationOccurred("success");
            showNotification(`Зачислено успешных платежей: ${result.updated}`, "success");
            await loadProfile();
        }
    } catch (err) {
        console.error("Error checking pending payments:", err);
    }
}

// Modal Logic
function openConfigModal(link) {
    const modal = document.getElementById('config-modal');
    const input = document.getElementById('modal-link');
    input.value = link;

    modal.classList.remove('hidden');
    // small delay to allow display:block to apply before opacity transition
    setTimeout(() => {
        modal.classList.remove('opacity-0');
    }, 10);
}

function closeConfigModal() {
    const modal = document.getElementById('config-modal');
    modal.classList.add('opacity-0');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300); // match transition duration
}

document.getElementById('modal-copy-link').addEventListener('click', () => {
    const input = document.getElementById('modal-link');
    input.select();
    input.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(input.value).then(() => {
        tg.HapticFeedback.impactOccurred("light");
        const btn = document.getElementById('modal-copy-link');
        const orig = btn.textContent;
        btn.textContent = "Скопировано!";
        btn.classList.replace('bg-blue-500', 'bg-green-500');
        setTimeout(() => {
            btn.textContent = orig;
            btn.classList.replace('bg-green-500', 'bg-blue-500');
        }, 2000);
    });
});

document.getElementById('btn-refresh-configs').addEventListener('click', async () => {
    tg.HapticFeedback.impactOccurred("light");
    const icon = document.querySelector('#btn-refresh-configs svg');
    icon.classList.add('animate-spin');
    await loadProfile();
    setTimeout(() => icon.classList.remove('animate-spin'), 500);
});

// Utils
function showNotification(message, type = 'info') {
    const colors = {
        success: 'bg-green-100 text-green-800 border-green-200',
        error: 'bg-red-100 text-red-800 border-red-200',
        info: 'bg-blue-100 text-blue-800 border-blue-200'
    };

    const div = document.createElement('div');
    div.className = `p-3 rounded-lg border text-sm fade-in mb-2 ${colors[type]}`;
    div.textContent = message;

    notifications.appendChild(div);

    setTimeout(() => {
        div.style.opacity = '0';
        div.style.transition = 'opacity 0.3s ease';
        setTimeout(() => div.remove(), 300);
    }, 5000);
}

function showLoading(show) {
    if (show) {
        loadingScreen.classList.remove('hidden');
    } else {
        loadingScreen.classList.add('hidden');
    }
}

// Start
init();
