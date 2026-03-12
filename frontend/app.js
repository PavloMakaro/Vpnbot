// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

// Set theme colors programmatically if needed
document.documentElement.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#ffffff');
document.documentElement.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#000000');
document.documentElement.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#999999');
document.documentElement.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#3390ec');
document.documentElement.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
document.documentElement.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color || '#f0f0f0');

// App Configuration
// REPLACE WITH YOUR ACTUAL ATLAS APP ID
const APP_ID = 'vpn_bot-xxxxx';
let app, user, currentUserProfile, currentConfigs;

// Main Initialization
async function init() {
    try {
        app = new Realm.App({ id: APP_ID });
        await authenticate();
        await loadDashboard();

        // Hide loading screen, show main app
        document.getElementById('loading-screen').style.display = 'none';
        document.getElementById('app').classList.remove('hidden');

        // Check for pending payments asynchronously
        checkPendingPayments();

    } catch (error) {
        console.error('Initialization error:', error);
        showToast('Ошибка подключения к серверу. Попробуйте позже.', 'error');
        // Handle mock local testing
        if (window.location.protocol === 'file:' || window.location.hostname === 'localhost') {
            handleMockLogin();
        }
    }
}

async function authenticate() {
    const initData = tg.initData || 'mock_init_data';

    // Custom function authentication via Stitch
    const credentials = Realm.Credentials.function({ initData });
    user = await app.logIn(credentials);
    console.log("Successfully logged in!", user.id);
}

async function loadDashboard() {
    // 1. Fetch Profile
    currentUserProfile = await user.functions.getProfile();

    if (currentUserProfile.error) {
        throw new Error(currentUserProfile.error);
    }

    // Update UI
    document.getElementById('user-name').textContent = currentUserProfile.first_name || 'Пользователь';
    document.getElementById('user-username').textContent = currentUserProfile.username ? `@${currentUserProfile.username}` : '';
    document.getElementById('user-avatar').textContent = (currentUserProfile.first_name || 'U').charAt(0).toUpperCase();

    document.getElementById('user-balance').textContent = `${currentUserProfile.balance} ₽`;
    document.getElementById('modal-balance').textContent = `${currentUserProfile.balance} ₽`;

    document.getElementById('user-sub-status').textContent = currentUserProfile.subscription_status;
    document.getElementById('sub-status-icon').textContent = currentUserProfile.days_left > 0 ? '✅' : '❌';

    // Referral section
    const refLink = `https://t.me/vpni50_bot?start=${currentUserProfile.id}`;
    document.getElementById('ref-link').textContent = refLink;
    document.getElementById('ref-count').textContent = currentUserProfile.referrals_count || 0;

    // 2. Fetch Configs & Periods
    currentConfigs = await user.functions.getConfigs();

    if (currentConfigs.error) {
        console.error(currentConfigs.error);
        return;
    }

    renderPeriods();
    renderConfigs();
}

function renderPeriods() {
    const container = document.getElementById('periods-container');
    container.innerHTML = '';

    const periods = currentConfigs.subscription_periods;
    const available = currentConfigs.available_counts;

    for (const [key, data] of Object.entries(periods)) {
        const count = available[key] || 0;
        const disabled = count === 0 || currentUserProfile.balance < data.price;
        const opacity = disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer active:scale-[0.98]';

        const card = document.createElement('div');
        card.className = `card !mb-0 transition-transform ${opacity}`;
        card.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <h3 class="font-bold text-lg">${data.days} дней</h3>
                    <p class="text-sm text-[var(--tg-theme-hint-color)]">Доступно конфигов: ${count}</p>
                </div>
                <div class="text-right">
                    <p class="font-bold text-[var(--tg-theme-button-color)]">${data.price} ₽</p>
                    ${count === 0 ? '<p class="text-xs text-red-500">Нет в наличии</p>' : ''}
                </div>
            </div>
        `;

        if (!disabled) {
            card.onclick = () => confirmPurchase(key, data);
        }

        container.appendChild(card);
    }
}

function renderConfigs() {
    const container = document.getElementById('configs-list');
    container.innerHTML = '';

    const configs = currentConfigs.used_configs || [];

    if (configs.length === 0) {
        container.innerHTML = '<p class="text-center text-[var(--tg-theme-hint-color)] py-8">У вас пока нет активных конфигов.</p>';
        return;
    }

    configs.reverse().forEach((config, idx) => {
        const item = document.createElement('div');
        item.className = 'card !mb-3';

        const dateStr = config.issue_date ? new Date(config.issue_date).toLocaleDateString() : 'N/A';

        item.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <h3 class="font-bold">VPN на ${currentConfigs.subscription_periods[config.period]?.days || 30} дней</h3>
                <span class="text-xs bg-[var(--tg-theme-bg-color)] px-2 py-1 rounded text-[var(--tg-theme-hint-color)]">${dateStr}</span>
            </div>
            <div class="bg-[var(--tg-theme-bg-color)] p-2 rounded text-xs break-all border border-[var(--tg-theme-hint-color)] border-opacity-20 mb-2 font-mono" id="config-link-${idx}">
                ${config.config_link}
            </div>
            <button onclick="copyToClipboard('${config.config_link}', 'config-link-${idx}')" class="btn-secondary !py-2 !text-sm flex justify-center items-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Копировать ссылку
            </button>
        `;
        container.appendChild(item);
    });
}

async function confirmPurchase(periodKey, data) {
    tg.showConfirm(`Подтвердите покупку подписки на ${data.days} дней за ${data.price} ₽. Средства будут списаны с вашего баланса.`, async (confirmed) => {
        if (confirmed) {
            try {
                tg.MainButton.showProgress();
                const result = await user.functions.buySubscription(periodKey);
                tg.MainButton.hideProgress();

                if (result.success) {
                    showToast('Подписка успешно куплена!', 'success');
                    hideModal('buy-modal');
                    await loadDashboard(); // Refresh data

                    // Show the new config automatically
                    setTimeout(() => showConfigsModal(), 500);
                } else {
                    tg.showAlert(result.error || 'Произошла ошибка при покупке.');
                }
            } catch (e) {
                tg.MainButton.hideProgress();
                console.error(e);
                tg.showAlert('Ошибка связи с сервером.');
            }
        }
    });
}

// Payment Methods
function setTopupAmount(amount) {
    document.getElementById('custom-amount').value = amount;
}

async function processTopup() {
    const input = document.getElementById('custom-amount');
    const amount = parseInt(input.value);

    if (isNaN(amount) || amount < 50 || amount > 50000) {
        tg.showAlert('Пожалуйста, введите сумму от 50 до 50000 ₽');
        return;
    }

    try {
        const btn = document.getElementById('pay-btn');
        btn.textContent = 'Создание платежа...';
        btn.disabled = true;
        btn.classList.add('opacity-50');

        // Generate Yookassa payment link
        const desc = `Пополнение баланса на ${amount} ₽`;
        const result = await user.functions.createPayment(amount, desc);

        if (result.error) {
            tg.showAlert(result.error);
        } else if (result.confirmationUrl) {
            // Open payment URL via Telegram
            tg.openLink(result.confirmationUrl);
            hideModal('topup-modal');
            showToast('Ожидаем оплату...', 'info');

            // Start polling for payment status
            pollPaymentStatus(result.paymentId);
        }

    } catch (e) {
        console.error(e);
        tg.showAlert('Ошибка создания платежа.');
    } finally {
        const btn = document.getElementById('pay-btn');
        btn.textContent = 'Оплатить через ЮKassa';
        btn.disabled = false;
        btn.classList.remove('opacity-50');
    }
}

async function pollPaymentStatus(paymentId) {
    let attempts = 0;
    const maxAttempts = 20; // 20 * 3s = 60s polling

    const interval = setInterval(async () => {
        attempts++;
        if (attempts >= maxAttempts) {
            clearInterval(interval);
            return;
        }

        try {
            const result = await user.functions.checkPayment(paymentId);
            if (result.status === 'succeeded') {
                clearInterval(interval);
                showToast(`Баланс успешно пополнен на ${result.amount} ₽!`, 'success');
                await loadDashboard();
            } else if (result.status === 'canceled') {
                clearInterval(interval);
                showToast('Платеж отменен.', 'error');
            }
        } catch (e) {
            console.error('Polling error', e);
        }
    }, 3000);
}

async function checkPendingPayments() {
    try {
        const result = await user.functions.checkPendingPayments();
        if (result && result.confirmed > 0) {
            showToast(`Успешно обработано платежей: ${result.confirmed}. Зачислено: ${result.total_added} ₽`, 'success');
            await loadDashboard();
        }
    } catch (e) {
        console.error("Failed to check pending payments:", e);
    }
}

// UI Utilities
function showModal(id) {
    const modal = document.getElementById(id);
    modal.classList.remove('hidden');
    // Prevent background scrolling
    document.body.style.overflow = 'hidden';
}

function hideModal(id) {
    const modal = document.getElementById(id);
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

function showBuyModal() { showModal('buy-modal'); }
function showTopupModal() { showModal('topup-modal'); }
function showConfigsModal() { showModal('configs-modal'); }

async function copyToClipboard(text, elementId) {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers/Telegram Webview
            const textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.style.position = "absolute";
            textArea.style.left = "-999999px";
            document.body.prepend(textArea);
            textArea.select();
            document.execCommand('copy');
            textArea.remove();
        }

        // Visual feedback
        if (elementId) {
            const el = document.getElementById(elementId);
            const originalBg = el.style.backgroundColor;
            el.style.backgroundColor = 'rgba(51, 144, 236, 0.2)';
            setTimeout(() => {
                el.style.backgroundColor = originalBg;
            }, 300);
        }

        showToast('Скопировано в буфер обмена!');
        tg.HapticFeedback.notificationOccurred('success');
    } catch (err) {
        console.error('Failed to copy text: ', err);
        showToast('Не удалось скопировать', 'error');
    }
}

function copyRefLink() {
    const link = document.getElementById('ref-link').textContent;
    copyToClipboard(link);
}

function showToast(msg, type = 'success') {
    const toast = document.getElementById('toast');
    const msgEl = document.getElementById('toast-msg');
    const iconEl = document.getElementById('toast-icon');

    msgEl.textContent = msg;

    if (type === 'success') {
        toast.className = 'fixed top-4 left-4 right-4 bg-green-500 text-white p-3 rounded-lg shadow-lg transform translate-y-0 transition-transform duration-300 z-[100] flex items-center';
        iconEl.textContent = '✅';
    } else if (type === 'error') {
        toast.className = 'fixed top-4 left-4 right-4 bg-red-500 text-white p-3 rounded-lg shadow-lg transform translate-y-0 transition-transform duration-300 z-[100] flex items-center';
        iconEl.textContent = '❌';
    } else {
        toast.className = 'fixed top-4 left-4 right-4 bg-blue-500 text-white p-3 rounded-lg shadow-lg transform translate-y-0 transition-transform duration-300 z-[100] flex items-center';
        iconEl.textContent = 'ℹ️';
    }

    setTimeout(() => {
        toast.style.transform = 'translateY(-150%)';
    }, 3000);
}

// Fallback logic for local testing
function handleMockLogin() {
    console.warn("Using mock local data for testing");
    document.getElementById('loading-screen').style.display = 'none';
    document.getElementById('app').classList.remove('hidden');

    currentUserProfile = {
        id: 'mock123',
        first_name: 'Local Tester',
        username: 'localtester',
        balance: 1500,
        days_left: 15,
        subscription_status: 'Активна еще 15 дней',
        referrals_count: 5
    };

    currentConfigs = {
        subscription_periods: {
            '1_month': { price: 50, days: 30 },
            '2_months': { price: 90, days: 60 }
        },
        available_counts: {
            '1_month': 10,
            '2_months': 5
        },
        used_configs: [
            { period: '1_month', config_link: 'vless://mock-link-1234567890?security=reality', issue_date: new Date() }
        ]
    };

    // Mock user object
    user = {
        functions: {
            getProfile: async () => currentUserProfile,
            getConfigs: async () => currentConfigs,
            buySubscription: async () => ({ success: true, config: currentConfigs.used_configs[0] }),
            createPayment: async () => ({ paymentId: 'mock_pay', confirmationUrl: 'https://yoomoney.ru' }),
            checkPayment: async () => ({ status: 'pending' }),
            checkPendingPayments: async () => ({ confirmed: 0 })
        }
    };

    // Update UI directly for mock
    document.getElementById('user-name').textContent = currentUserProfile.first_name;
    document.getElementById('user-balance').textContent = `${currentUserProfile.balance} ₽`;
    document.getElementById('modal-balance').textContent = `${currentUserProfile.balance} ₽`;
    document.getElementById('user-sub-status').textContent = currentUserProfile.subscription_status;

    renderPeriods();
    renderConfigs();
}

// Init App
init();