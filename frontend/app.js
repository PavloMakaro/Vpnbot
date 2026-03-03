// App Config
const REALM_APP_ID = "application-0-XXXXX"; // TO BE REPLACED WITH ACTUAL APP ID
const app = new Realm.App({ id: REALM_APP_ID });

let tg = window.Telegram.WebApp;
tg.expand();

// DOM Elements
const loadingEl = document.getElementById('loading');
const appContainer = document.getElementById('app-container');
const userNameEl = document.getElementById('user-name');
const userInitialEl = document.getElementById('user-initial');
const userUsernameEl = document.getElementById('user-username');
const userBalanceEl = document.getElementById('user-balance');
const subStatusEl = document.getElementById('sub-status');
const configsListEl = document.getElementById('configs-list');

// Modals
const modalTopup = document.getElementById('modal-topup');
const modalTopupContent = document.getElementById('modal-topup-content');
const modalSub = document.getElementById('modal-sub');
const modalSubContent = document.getElementById('modal-sub-content');
const modalConfig = document.getElementById('modal-config');
const modalConfigContent = document.getElementById('modal-config-content');

// Inputs
const customAmountInput = document.getElementById('custom-amount');
const btnPay = document.getElementById('btn-pay');
const subOptionsContainer = document.getElementById('sub-options');
const newConfigLinkEl = document.getElementById('new-config-link');

// State
let selectedAmount = 0;
let subscriptionPeriods = {};

// Helpers
function showToast(msg) {
    const toast = document.getElementById('toast');
    document.getElementById('toast-msg').innerText = msg;
    toast.style.opacity = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 3000);
}

function openModal(modalId, contentId) {
    const modal = document.getElementById(modalId);
    const content = document.getElementById(contentId);
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    setTimeout(() => {
        content.style.opacity = '1';
        content.style.transform = 'scale(1)';
    }, 10);
}

function closeModal(modalId, contentId) {
    const modal = document.getElementById(modalId);
    const content = document.getElementById(contentId);
    content.style.opacity = '0';
    content.style.transform = 'scale(0.95)';
    setTimeout(() => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }, 300);
}

document.querySelectorAll('.close-modal').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const modal = e.target.closest('.fixed');
        const content = modal.querySelector('.transform');
        closeModal(modal.id, content.id);
    });
});

// Main Init Flow
async function initApp() {
    try {
        // 1. Authenticate with Realm using Telegram initData
        const credentials = Realm.Credentials.customFunction({
            initData: tg.initData
        });

        const user = await app.logIn(credentials);

        // 2. Fetch Profile Data
        await loadProfile();

        // 3. Setup UI interactions
        setupUI();

        // Hide loader, show app
        loadingEl.style.opacity = '0';
        setTimeout(() => {
            loadingEl.style.display = 'none';
            appContainer.classList.remove('hidden');
        }, 500);

    } catch (err) {
        console.error("Initialization error:", err);
        loadingEl.innerHTML = `<p class="text-red-500 font-bold p-4 text-center">Ошибка загрузки: ${err.message}</p>`;
    }
}

async function loadProfile() {
    if (!app.currentUser) return;

    try {
        const profile = await app.currentUser.functions.getProfile();

        userNameEl.innerText = profile.first_name;
        userInitialEl.innerText = profile.first_name ? profile.first_name.charAt(0).toUpperCase() : '?';
        userUsernameEl.innerText = `@${profile.username}`;
        userBalanceEl.innerText = profile.balance;
        subStatusEl.innerText = profile.subscription_status;

        // Load configs
        renderConfigs(profile.used_configs);

    } catch (err) {
        console.error("Failed to load profile", err);
        showToast("Не удалось загрузить профиль");
    }
}

function renderConfigs(configs) {
    if (!configs || configs.length === 0) {
        configsListEl.innerHTML = `<p class="text-sm text-gray-400 text-center py-4 bg-gray-900 rounded-lg border border-gray-700">У вас пока нет выданных конфигов.</p>`;
        return;
    }

    let html = '';
    configs.reverse().forEach((conf, idx) => {
        const date = new Date(conf.issue_date).toLocaleDateString('ru-RU');
        html += `
            <div class="bg-gray-900 rounded-lg p-4 border border-gray-700 mb-3 hover:border-blue-500 transition-colors">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-sm text-blue-400">${conf.config_name}</h3>
                    <span class="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">${date}</span>
                </div>
                <div class="bg-black p-2 rounded text-xs text-gray-400 break-all border border-gray-800 font-mono select-all">
                    ${conf.config_link}
                </div>
                <button class="copy-btn w-full mt-2 text-xs text-blue-400 hover:text-white transition-colors" data-link="${conf.config_link}">
                    📋 Копировать
                </button>
            </div>
        `;
    });

    configsListEl.innerHTML = html;

    // Attach copy events
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            navigator.clipboard.writeText(e.target.dataset.link);
            showToast("Скопировано!");
        });
    });
}

function setupUI() {
    // Topup Flow
    document.getElementById('btn-topup').addEventListener('click', () => {
        openModal('modal-topup', 'modal-topup-content');
    });

    document.querySelectorAll('.amount-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.amount-btn').forEach(b => {
                b.classList.remove('bg-blue-600', 'border-blue-400');
                b.classList.add('bg-gray-700');
            });
            e.target.classList.remove('bg-gray-700');
            e.target.classList.add('bg-blue-600', 'border', 'border-blue-400');

            selectedAmount = parseInt(e.target.dataset.amount);
            customAmountInput.value = '';
            btnPay.innerText = `Оплатить ${selectedAmount} ₽`;
            btnPay.disabled = false;
        });
    });

    customAmountInput.addEventListener('input', (e) => {
        document.querySelectorAll('.amount-btn').forEach(b => {
            b.classList.remove('bg-blue-600', 'border-blue-400');
            b.classList.add('bg-gray-700');
        });

        const val = parseInt(e.target.value);
        if (val && val >= 50) {
            selectedAmount = val;
            btnPay.innerText = `Оплатить ${selectedAmount} ₽`;
            btnPay.disabled = false;
        } else {
            selectedAmount = 0;
            btnPay.innerText = 'Оплатить через ЮKassa';
            btnPay.disabled = true;
        }
    });

    btnPay.addEventListener('click', async () => {
        if (selectedAmount < 50) return;

        btnPay.disabled = true;
        btnPay.innerHTML = '<span class="animate-pulse">Создание платежа...</span>';

        try {
            const result = await app.currentUser.functions.createPayment(selectedAmount, "https://t.me/vpni50_bot");

            // Redirect to Yookassa
            tg.openLink(result.confirmationUrl);

            closeModal('modal-topup', 'modal-topup-content');
            showToast("Перенаправление на оплату...");

            // Polling for payment status (in real app, use webhook or manual check button)
            checkPaymentStatus(result.paymentId);

        } catch (err) {
            console.error(err);
            showToast("Ошибка создания платежа");
        } finally {
            btnPay.disabled = false;
            btnPay.innerText = `Оплатить ${selectedAmount} ₽`;
        }
    });

    // Subscription Flow
    document.getElementById('btn-buy-sub').addEventListener('click', async () => {
        openModal('modal-sub', 'modal-sub-content');
        subOptionsContainer.innerHTML = '<p class="text-center text-gray-400 py-4">Загрузка тарифов...</p>';

        try {
            const data = await app.currentUser.functions.getConfigs();
            subscriptionPeriods = data.subscriptionPeriods;

            let html = '';
            for (const [key, period] of Object.entries(subscriptionPeriods)) {
                html += `
                    <button class="buy-period-btn w-full bg-gray-700 hover:bg-gray-600 border border-gray-600 hover:border-blue-500 rounded-xl p-4 flex justify-between items-center transition-all group" data-period="${key}" data-price="${period.price}">
                        <div>
                            <span class="block font-bold text-lg text-left">${period.days} дней</span>
                            <span class="block text-sm text-gray-400 text-left group-hover:text-blue-300">VPN Конфиг</span>
                        </div>
                        <div class="bg-gray-900 py-2 px-4 rounded-lg font-bold text-green-400 border border-gray-800">
                            ${period.price} ₽
                        </div>
                    </button>
                `;
            }
            subOptionsContainer.innerHTML = html;

            // Attach buy events
            document.querySelectorAll('.buy-period-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const target = e.currentTarget;
                    const period = target.dataset.period;
                    const price = parseInt(target.dataset.price);

                    const currentBalance = parseInt(userBalanceEl.innerText);

                    if (currentBalance < price) {
                        showToast(`Недостаточно средств. Нужно еще ${price - currentBalance} ₽`);
                        closeModal('modal-sub', 'modal-sub-content');
                        setTimeout(() => openModal('modal-topup', 'modal-topup-content'), 400);
                        return;
                    }

                    // Proceed to buy
                    const originalHtml = target.innerHTML;
                    target.innerHTML = '<div class="w-full text-center py-2"><span class="animate-pulse">Оформление...</span></div>';
                    document.querySelectorAll('.buy-period-btn').forEach(b => b.disabled = true);

                    try {
                        const result = await app.currentUser.functions.buySubscription(period);
                        if (result.success) {
                            closeModal('modal-sub', 'modal-sub-content');

                            // Update UI
                            userBalanceEl.innerText = result.newBalance;
                            await loadProfile(); // Reload to get new status and configs list

                            // Show success modal
                            newConfigLinkEl.innerText = result.config.link;
                            setTimeout(() => openModal('modal-config', 'modal-config-content'), 400);
                            tg.HapticFeedback.notificationOccurred('success');
                        }
                    } catch (err) {
                        console.error(err);
                        showToast(err.message || "Ошибка при покупке");
                        target.innerHTML = originalHtml;
                        document.querySelectorAll('.buy-period-btn').forEach(b => b.disabled = false);
                    }
                });
            });

        } catch (err) {
            console.error(err);
            subOptionsContainer.innerHTML = '<p class="text-center text-red-400 py-4">Ошибка загрузки</p>';
        }
    });

    document.getElementById('btn-copy-config').addEventListener('click', () => {
        navigator.clipboard.writeText(newConfigLinkEl.innerText);
        showToast("Ссылка скопирована!");
        tg.HapticFeedback.impactOccurred('light');
    });
}

async function checkPaymentStatus(paymentId) {
    let attempts = 0;
    const maxAttempts = 20; // 20 * 5s = 100s

    const interval = setInterval(async () => {
        try {
            const res = await app.currentUser.functions.checkPayment(paymentId);
            if (res.status === 'succeeded') {
                clearInterval(interval);
                showToast("Баланс успешно пополнен!");
                tg.HapticFeedback.notificationOccurred('success');
                await loadProfile();
            } else if (res.status === 'canceled') {
                clearInterval(interval);
                showToast("Платеж отменен");
            }
        } catch (e) {
            console.error("Payment check error", e);
        }

        attempts++;
        if (attempts >= maxAttempts) {
            clearInterval(interval);
        }
    }, 5000);
}

// Start
document.addEventListener('DOMContentLoaded', initApp);