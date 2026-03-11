// Initialize Telegram Web App
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

// Realm App Configuration
// Replace with your actual App ID
const REALM_APP_ID = "application-0-XXXXX"; // You will configure this properly later
const app = new Realm.App({ id: REALM_APP_ID });

// Mock data for local testing
const isLocal = window.location.protocol === 'file:' || window.location.hostname === 'localhost';
let mockProfile = {
    id: "123",
    username: "testuser",
    first_name: "Test",
    balance: 50,
    days_left: 0,
    subscription_end: null,
    used_configs: []
};
let mockConfigs = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
};

// UI Elements
const els = {
    loadingView: document.getElementById('loadingView'),
    mainView: document.getElementById('mainView'),
    topupView: document.getElementById('topupView'),
    buySubView: document.getElementById('buySubView'),

    statusBadge: document.getElementById('statusBadge'),
    subscriptionInfo: document.getElementById('subscriptionInfo'),
    balanceAmount: document.getElementById('balanceAmount'),
    buyBalance: document.getElementById('buyBalance'),
    configsList: document.getElementById('configsList'),
    plansContainer: document.getElementById('plansContainer'),

    btnTopup: document.getElementById('btnTopup'),
    btnBuySub: document.getElementById('btnBuySub'),
    btnBackFromTopup: document.getElementById('btnBackFromTopup'),
    btnBackFromBuy: document.getElementById('btnBackFromBuy'),
    btnPayYookassa: document.getElementById('btnPayYookassa'),
    customAmount: document.getElementById('customAmount'),
    paySpinner: document.getElementById('paySpinner')
};

// Setup Event Listeners
function setupEvents() {
    els.btnTopup.addEventListener('click', () => showView(els.topupView));
    els.btnBuySub.addEventListener('click', () => {
        showView(els.buySubView);
        renderPlans();
    });

    els.btnBackFromTopup.addEventListener('click', () => showView(els.mainView));
    els.btnBackFromBuy.addEventListener('click', () => showView(els.mainView));

    // Topup Amounts
    document.querySelectorAll('.topup-amount').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const amount = e.target.getAttribute('data-amount');
            els.customAmount.value = amount;
            createPayment(amount);
        });
    });

    els.btnPayYookassa.addEventListener('click', () => {
        const val = parseInt(els.customAmount.value);
        if (isNaN(val) || val < 50 || val > 50000) {
            tg.showAlert("Введите сумму от 50 до 50000 ₽");
            return;
        }
        createPayment(val);
    });
}

// Navigation Helper
function showView(view) {
    [els.mainView, els.topupView, els.buySubView].forEach(v => v.classList.add('hidden'));
    view.classList.remove('hidden');
    if (view === els.mainView) {
        tg.BackButton.hide();
        tg.MainButton.hide();
    } else {
        tg.BackButton.show();
        tg.BackButton.onClick(() => showView(els.mainView));
    }
}

// Format Date
function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch {
        return dateStr;
    }
}

// Initialize Application
async function initApp() {
    try {
        setupEvents();

        if (isLocal) {
            console.log("Running in local mock mode");
            setTimeout(() => {
                updateProfileUI(mockProfile);
                els.loadingView.classList.add('hidden');
                showView(els.mainView);
            }, 500);
            return;
        }

        // Authenticate with Realm via Custom JWT (InitData)
        if (!tg.initData) {
            throw new Error("Missing initData. App must be run inside Telegram.");
        }

        const credentials = Realm.Credentials.customFunction({ initData: tg.initData });
        const user = await app.logIn(credentials);

        // Check pending payments before loading profile
        await checkPendingPayments();

        await loadProfile();

    } catch (err) {
        console.error("Initialization error:", err);
        tg.showAlert(`Ошибка авторизации: ${err.message}`);
    }
}

async function checkPendingPayments() {
    if (isLocal) return;
    try {
        const res = await app.currentUser.functions.checkPendingPayments();
        if (res && res.success && res.updated > 0) {
            tg.HapticFeedback.notificationOccurred('success');
            tg.showAlert(`✅ Успешно обработано платежей: ${res.updated}. Баланс пополнен!`);
        }
    } catch (err) {
        console.error("Pending payments check error:", err);
    }
}

async function loadProfile() {
    try {
        const profile = await app.currentUser.functions.getProfile();
        updateProfileUI(profile);

        els.loadingView.classList.add('hidden');
        showView(els.mainView);
    } catch (err) {
        console.error(err);
        tg.showAlert(`Ошибка загрузки профиля: ${err.message}`);
    }
}

function updateProfileUI(profile) {
    // Balance
    els.balanceAmount.textContent = profile.balance;
    els.buyBalance.textContent = `${profile.balance} ₽`;

    // Status Badge
    if (profile.days_left > 0) {
        els.statusBadge.textContent = `Активна (${profile.days_left} дн.)`;
        els.statusBadge.className = 'inline-block px-3 py-1 rounded-full text-sm font-semibold mb-2 bg-green-100 text-green-800';
        els.subscriptionInfo.textContent = `До ${formatDate(profile.subscription_end)}`;
    } else {
        els.statusBadge.textContent = 'Нет подписки';
        els.statusBadge.className = 'inline-block px-3 py-1 rounded-full text-sm font-semibold mb-2 bg-red-100 text-red-800';
        els.subscriptionInfo.textContent = 'Купите подписку для доступа';
    }

    // Configs List
    els.configsList.innerHTML = '';
    if (!profile.used_configs || profile.used_configs.length === 0) {
        els.configsList.innerHTML = '<p class="text-sm opacity-60">У вас пока нет конфигов.</p>';
    } else {
        profile.used_configs.forEach((cfg, idx) => {
            const html = `
                <div class="p-3 border rounded-lg bg-white dark:bg-gray-800 shadow-sm relative overflow-hidden">
                    <div class="font-bold mb-1">${cfg.config_name}</div>
                    <div class="text-xs opacity-70 mb-2">Выдан: ${cfg.issue_date}</div>
                    <div class="bg-gray-100 dark:bg-gray-700 p-2 rounded text-xs font-mono break-all select-all">
                        ${cfg.config_link}
                    </div>
                    <button class="copy-btn mt-2 text-xs bg-[var(--tg-theme-button-color)] text-white px-3 py-1 rounded w-full" data-link="${cfg.config_link}">Копировать ссылку</button>
                </div>
            `;
            els.configsList.insertAdjacentHTML('beforeend', html);
        });

        // Copy event listeners
        document.querySelectorAll('.copy-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const link = e.target.getAttribute('data-link');
                navigator.clipboard.writeText(link).then(() => {
                    e.target.textContent = 'Скопировано!';
                    setTimeout(() => e.target.textContent = 'Копировать ссылку', 2000);
                    tg.HapticFeedback.impactOccurred('medium');
                });
            });
        });
    }
}

async function renderPlans() {
    els.plansContainer.innerHTML = '<div class="loader"></div>';
    try {
        let configs = mockConfigs;
        if (!isLocal) {
            configs = await app.currentUser.functions.getConfigs();
        }

        els.plansContainer.innerHTML = '';
        for (const [key, data] of Object.entries(configs)) {
            const btn = document.createElement('button');
            btn.className = 'w-full text-left p-4 border rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors flex justify-between items-center';
            btn.innerHTML = `
                <div>
                    <div class="font-bold text-lg">${data.days} Дней</div>
                    <div class="text-sm opacity-70">Надежный VPN без лимитов</div>
                </div>
                <div class="font-bold text-[var(--tg-theme-button-color)]">${data.price} ₽</div>
            `;

            btn.addEventListener('click', () => handleBuy(key, data.price, data.days));
            els.plansContainer.appendChild(btn);
        }
    } catch (err) {
        console.error(err);
        els.plansContainer.innerHTML = `<p class="text-red-500">Ошибка: ${err.message}</p>`;
    }
}

async function handleBuy(periodKey, price, days) {
    tg.showConfirm(`Вы уверены, что хотите купить подписку на ${days} дней за ${price} ₽?\n\nСредства будут списаны с вашего баланса.`, async (confirmed) => {
        if (!confirmed) return;

        if (isLocal) {
            if (mockProfile.balance < price) {
                tg.showAlert("Недостаточно средств. Пополните баланс.");
                return;
            }
            mockProfile.balance -= price;
            mockProfile.days_left += days;
            mockProfile.used_configs.push({
                config_name: `Config_${periodKey}_1`,
                config_link: `vless://mock-link-${Date.now()}`,
                issue_date: new Date().toISOString()
            });
            tg.showAlert("Успешно куплено!");
            updateProfileUI(mockProfile);
            showView(els.mainView);
            return;
        }

        tg.MainButton.text = "ОБРАБОТКА...";
        tg.MainButton.show();
        tg.MainButton.showProgress();

        try {
            const result = await app.currentUser.functions.buySubscription(periodKey);
            if (result.success) {
                tg.HapticFeedback.notificationOccurred('success');
                tg.showAlert("Подписка успешно оформлена! Конфиг добавлен в 'Мои конфиги'.");
                await loadProfile();
            } else {
                tg.HapticFeedback.notificationOccurred('error');
                tg.showAlert(result.error || "Ошибка при покупке.");
            }
        } catch (err) {
            tg.showAlert(`Системная ошибка: ${err.message}`);
        } finally {
            tg.MainButton.hide();
        }
    });
}

async function createPayment(amount) {
    if (isLocal) {
        mockProfile.balance += parseInt(amount);
        tg.showAlert(`[Mock] Баланс пополнен на ${amount} ₽`);
        updateProfileUI(mockProfile);
        showView(els.mainView);
        return;
    }

    els.paySpinner.classList.remove('hidden');
    els.btnPayYookassa.disabled = true;

    try {
        const res = await app.currentUser.functions.createPayment(amount);
        if (res.confirmationUrl) {
            tg.openLink(res.confirmationUrl);
            // Prompt the user to check their balance when they return
            tg.showConfirm("Вы были перенаправлены на страницу оплаты. После успешной оплаты нажмите 'ОК', чтобы обновить баланс.", async (confirmed) => {
                if (confirmed) {
                    await checkPendingPayments();
                    await loadProfile();
                    showView(els.mainView);
                }
            });
        } else {
            throw new Error("Confirmation URL not received");
        }
    } catch (err) {
        console.error(err);
        tg.showAlert(`Ошибка платежа: ${err.message}`);
    } finally {
        els.paySpinner.classList.add('hidden');
        els.btnPayYookassa.disabled = false;
    }
}

// Start app
document.addEventListener('DOMContentLoaded', initApp);
