// app.js

const REALM_APP_ID = "application-0-yookassa"; // Replace with your actual Realm App ID

let app;
let currentUser;
let telegramUser;
let currentBalance = 0;
let pollingInterval = null;

// UI Elements
const els = {
    app: document.getElementById('app'),
    loadingView: document.getElementById('loadingView'),
    dashboardView: document.getElementById('dashboardView'),
    buyView: document.getElementById('buyView'),
    topupView: document.getElementById('topupView'),

    // Dashboard
    userName: document.getElementById('userName'),
    userBalance: document.getElementById('userBalance'),
    userSubEnd: document.getElementById('userSubEnd'),
    activeConfigsSection: document.getElementById('activeConfigsSection'),
    configsList: document.getElementById('configsList'),
    btnBuyVpn: document.getElementById('btnBuyVpn'),
    btnTopup: document.getElementById('btnTopup'),

    // Buy View
    btnBackFromBuy: document.getElementById('btnBackFromBuy'),
    subscriptionOptions: document.getElementById('subscriptionOptions'),
    loadingConfigsView: document.getElementById('loadingConfigsView'),

    // Topup View
    btnBackFromTopup: document.getElementById('btnBackFromTopup'),
    topupCurrentBalance: document.getElementById('topupCurrentBalance'),
    amountBtns: document.querySelectorAll('.amount-btn'),
    customAmountContainer: document.getElementById('customAmountContainer'),
    customAmountInput: document.getElementById('customAmountInput'),
    btnProceedTopup: document.getElementById('btnProceedTopup'),

    // Instructions Modal
    instructionsModal: document.getElementById('instructionsModal'),
    instructionsContent: document.getElementById('instructionsContent'),
    btnCloseInstructions: document.getElementById('btnCloseInstructions')
};

// --- Initialization ---

async function init() {
    console.log("Initializing App...");

    // 1. Initialize Telegram WebApp
    const tg = window.Telegram.WebApp;
    tg.expand();
    tg.ready();

    // Mock user for local testing if not running in Telegram
    if (!tg.initDataUnsafe || !tg.initDataUnsafe.user) {
        console.warn("Running outside Telegram. Mocking user.");
        telegramUser = {
            id: 8320218178, // Default Admin ID for testing
            first_name: "Test User",
            username: "testuser",
            language_code: "ru"
        };
        // Mock initData
        tg.initData = "query_id=mock_query_id&user=%7B%22id%22%3A8320218178%2C%22first_name%22%3A%22Test%20User%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22testuser%22%2C%22language_code%22%3A%22ru%22%7D&auth_date=1680000000&hash=mock_hash";
    } else {
        telegramUser = tg.initDataUnsafe.user;
    }

    // Set theme colors based on TG settings
    document.documentElement.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#ffffff');
    document.documentElement.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#000000');
    document.documentElement.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#999999');
    document.documentElement.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color || '#3390ec');
    document.documentElement.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#3390ec');
    document.documentElement.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
    document.documentElement.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color || '#f3f4f6');

    // 2. Initialize Realm (MongoDB Atlas App Services)
    try {
        app = new Realm.App({ id: REALM_APP_ID });
        console.log("Realm App initialized");

        await authenticateWithTelegram(tg.initData);
        await loadDashboard();

        // Start polling for pending payments
        startPaymentPolling();
    } catch (error) {
        console.error("Initialization error:", error);
        tg.showAlert("Ошибка подключения к серверу. Попробуйте перезапустить приложение.");
        // Hide loading even on error so user isn't stuck forever
        showView(els.dashboardView);
    }

    setupEventListeners(tg);
}

// --- Realm Authentication ---

async function authenticateWithTelegram(initData) {
    console.log("Authenticating with Telegram initData...");
    try {
        // Custom Function Auth expects the initData string
        const credentials = Realm.Credentials.function({
            initData: initData
        });

        currentUser = await app.logIn(credentials);
        console.log("Successfully logged in!", currentUser.id);
        return currentUser;
    } catch (err) {
        console.error("Failed to log in", err);
        throw err;
    }
}

// --- Data Loading ---

async function loadDashboard() {
    try {
        console.log("Loading dashboard data...");
        // Call backend function getProfile
        const profileData = await currentUser.functions.getProfile();
        console.log("Profile data:", profileData);

        // Update UI
        els.userName.textContent = profileData.first_name || profileData.username || "Пользователь";
        currentBalance = profileData.balance || 0;
        els.userBalance.textContent = currentBalance;

        // Format subscription date (replace space with T for Safari compatibility)
        if (profileData.subscription_end) {
            const dateStr = profileData.subscription_end.replace(' ', 'T');
            const subDate = new Date(dateStr);
            const now = new Date();

            if (subDate > now) {
                els.userSubEnd.textContent = subDate.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
                els.userSubEnd.className = "font-bold text-green-600 dark:text-green-400";
            } else {
                els.userSubEnd.textContent = "Истекла";
                els.userSubEnd.className = "font-medium text-red-500";
            }
        } else {
            els.userSubEnd.textContent = "Нет подписки";
            els.userSubEnd.className = "font-medium text-hint";
        }

        // Render Configs
        if (profileData.used_configs && profileData.used_configs.length > 0) {
            renderConfigs(profileData.used_configs);
            els.activeConfigsSection.classList.remove('hidden');
        } else {
            els.activeConfigsSection.classList.add('hidden');
        }

        showView(els.dashboardView);

    } catch (error) {
        console.error("Error loading profile:", error);
        window.Telegram.WebApp.showAlert("Не удалось загрузить данные профиля.");
        showView(els.dashboardView);
    }
}

function renderConfigs(configs) {
    els.configsList.innerHTML = '';

    // Show only the most recent configs (e.g., reverse order)
    const reversed = [...configs].reverse();

    reversed.forEach(config => {
        const div = document.createElement('div');
        div.className = 'p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm';

        let linkHtml = '';
        if (config.config_link) {
            linkHtml = `
                <div class="mt-2 flex space-x-2">
                    <button class="flex-1 btn bg-green-500 hover:bg-green-600 text-sm py-2 px-3 copy-btn" data-link="${config.config_link}">Копировать ссылку</button>
                    <button class="flex-1 btn btn-secondary text-sm py-2 px-3 instructions-btn">Инструкция</button>
                </div>
            `;
        }

        const issueDate = config.issue_date ? new Date(config.issue_date.replace(' ', 'T')).toLocaleDateString('ru-RU') : 'Н/Д';
        const periodText = config.period === '1_month' ? '30 дней' : (config.period === '2_months' ? '60 дней' : (config.period === '3_months' ? '90 дней' : config.period));

        div.innerHTML = `
            <div class="font-medium text-sm text-gray-800 dark:text-gray-200">${config.config_name || 'VPN Конфиг'}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400 mt-1 flex justify-between">
                <span>Период: ${periodText}</span>
                <span>Выдан: ${issueDate}</span>
            </div>
            ${linkHtml}
        `;

        els.configsList.appendChild(div);
    });

    // Add event listeners to newly created buttons
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const link = e.target.getAttribute('data-link');
            copyToClipboard(link, e.target);
        });
    });

    document.querySelectorAll('.instructions-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            showInstructionsModal();
        });
    });
}

// --- Payment & Subscription Actions ---

async function loadSubscriptionOptions() {
    els.subscriptionOptions.innerHTML = '';
    els.loadingConfigsView.classList.remove('hidden');

    try {
        const configs = await currentUser.functions.getConfigs();
        els.loadingConfigsView.classList.add('hidden');

        for (const [key, data] of Object.entries(configs)) {
            const div = document.createElement('div');
            div.className = 'card flex justify-between items-center cursor-pointer transition-colors duration-200 hover:bg-gray-200 dark:hover:bg-gray-700';

            // Disable option if not enough balance
            const isAffordable = currentBalance >= data.price;
            if (!isAffordable) {
                div.classList.add('opacity-50', 'cursor-not-allowed');
            }

            div.innerHTML = `
                <div>
                    <div class="font-bold text-lg">${data.days} дней</div>
                    <div class="text-sm text-gray-500">${data.price} ₽</div>
                </div>
                <div>
                    ${isAffordable ?
                        `<button class="btn btn-sm text-sm px-4 py-1 buy-sub-btn" data-period="${key}" data-price="${data.price}">Купить</button>` :
                        `<button class="btn btn-sm btn-secondary text-sm px-4 py-1" disabled>Мало средств</button>`
                    }
                </div>
            `;

            els.subscriptionOptions.appendChild(div);
        }

        document.querySelectorAll('.buy-sub-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const period = e.target.getAttribute('data-period');
                const price = e.target.getAttribute('data-price');
                await confirmPurchase(period, price, e.target);
            });
        });

    } catch (error) {
        console.error("Error loading configs:", error);
        els.loadingConfigsView.classList.add('hidden');
        window.Telegram.WebApp.showAlert("Ошибка загрузки тарифов.");
    }
}

async function confirmPurchase(period, price, buttonElem) {
    const tg = window.Telegram.WebApp;

    tg.showConfirm(`Подтверждаете покупку подписки за ${price} ₽? Средства будут списаны с баланса.`, async (confirmed) => {
        if (!confirmed) return;

        buttonElem.disabled = true;
        buttonElem.textContent = 'Обработка...';

        try {
            const result = await currentUser.functions.buySubscription(period);

            if (result.success) {
                tg.showAlert(`Успешно! Ваш баланс: ${result.new_balance} ₽. Подписка активна до ${result.subscription_end}. Конфиг добавлен в профиль.`);
                await loadDashboard(); // Reload data
            } else {
                tg.showAlert(`Ошибка: ${result.error}`);
                buttonElem.disabled = false;
                buttonElem.textContent = 'Купить';
            }
        } catch (error) {
            console.error("Purchase error:", error);
            tg.showAlert("Произошла системная ошибка при покупке. Попробуйте позже.");
            buttonElem.disabled = false;
            buttonElem.textContent = 'Купить';
        }
    });
}

// --- Topup Process ---

let selectedTopupAmount = 0;

function handleTopupSelection(e) {
    const tg = window.Telegram.WebApp;

    // Reset selection styling
    els.amountBtns.forEach(b => {
        b.classList.remove('ring-2', 'ring-blue-500', 'border-blue-500');
        b.classList.add('btn-secondary');
        b.classList.remove('bg-blue-500', 'text-white');
    });

    const btn = e.target;
    btn.classList.add('ring-2', 'ring-blue-500', 'border-blue-500');

    const amountVal = btn.getAttribute('data-amount');

    if (amountVal === 'custom') {
        els.customAmountContainer.classList.remove('hidden');
        selectedTopupAmount = parseInt(els.customAmountInput.value) || 0;
        els.customAmountInput.focus();
    } else {
        els.customAmountContainer.classList.add('hidden');
        selectedTopupAmount = parseInt(amountVal);
    }

    validateTopupAmount();
}

function validateTopupAmount() {
    if (selectedTopupAmount >= 50 && selectedTopupAmount <= 50000) {
        els.btnProceedTopup.disabled = false;
        els.btnProceedTopup.textContent = `Оплатить ${selectedTopupAmount} ₽`;
    } else {
        els.btnProceedTopup.disabled = true;
        els.btnProceedTopup.textContent = 'Выберите сумму';
    }
}

async function proceedToPayment() {
    if (selectedTopupAmount < 50) return;

    const tg = window.Telegram.WebApp;
    els.btnProceedTopup.disabled = true;
    els.btnProceedTopup.textContent = 'Создание платежа...';

    try {
        const result = await currentUser.functions.createPayment(selectedTopupAmount);

        if (result.success && result.confirmation_url) {
            // Open payment URL
            tg.openLink(result.confirmation_url);

            // Show alert and go back to dashboard
            tg.showAlert("Платеж создан. После успешной оплаты баланс обновится автоматически в течение минуты.");
            showView(els.dashboardView);

            // Force an immediate check
            setTimeout(() => checkPendingPayments(), 5000);

        } else {
            throw new Error(result.error || "Неизвестная ошибка создания платежа");
        }
    } catch (error) {
        console.error("Payment creation error:", error);
        tg.showAlert(`Ошибка: ${error.message}`);
    } finally {
        els.btnProceedTopup.disabled = false;
        els.btnProceedTopup.textContent = `Оплатить ${selectedTopupAmount} ₽`;
    }
}

async function checkPendingPayments() {
    if (!currentUser) return;

    console.log("Checking for pending payments...");
    try {
        const result = await currentUser.functions.checkPendingPayments();
        if (result && result.processed_count > 0) {
            console.log(`Processed ${result.processed_count} payments. Reloading dashboard.`);
            // A payment went through! Reload user data.
            await loadDashboard();
            window.Telegram.WebApp.showAlert(`Ваш баланс успешно пополнен!`);
        }
    } catch (error) {
        console.error("Error polling payments:", error);
    }
}

function startPaymentPolling() {
    // Clear any existing interval
    if (pollingInterval) clearInterval(pollingInterval);

    // Poll every 30 seconds
    pollingInterval = setInterval(checkPendingPayments, 30000);
}

// --- Navigation & Utilities ---

function showView(viewElement) {
    // Hide all
    els.loadingView.classList.add('hidden');
    els.dashboardView.classList.add('hidden');
    els.buyView.classList.add('hidden');
    els.topupView.classList.add('hidden');

    // Show requested
    viewElement.classList.remove('hidden');

    // Handle back button visibility in TG App
    const tg = window.Telegram.WebApp;
    if (viewElement === els.dashboardView) {
        tg.BackButton.hide();
    } else {
        tg.BackButton.show();
    }
}

function setupEventListeners(tg) {
    // TG Back button integration
    tg.BackButton.onClick(() => {
        showView(els.dashboardView);
    });

    // Dashboard Navigation
    els.btnBuyVpn.addEventListener('click', () => {
        showView(els.buyView);
        loadSubscriptionOptions();
    });

    els.btnTopup.addEventListener('click', () => {
        els.topupCurrentBalance.textContent = currentBalance;
        showView(els.topupView);

        // Reset topup state
        els.amountBtns.forEach(b => {
            b.classList.remove('ring-2', 'ring-blue-500', 'border-blue-500');
        });
        els.customAmountContainer.classList.add('hidden');
        els.customAmountInput.value = '';
        selectedTopupAmount = 0;
        validateTopupAmount();
    });

    // Buy View Navigation
    els.btnBackFromBuy.addEventListener('click', () => showView(els.dashboardView));

    // Topup View Navigation & Logic
    els.btnBackFromTopup.addEventListener('click', () => showView(els.dashboardView));

    els.amountBtns.forEach(btn => {
        btn.addEventListener('click', handleTopupSelection);
    });

    els.customAmountInput.addEventListener('input', (e) => {
        selectedTopupAmount = parseInt(e.target.value) || 0;
        validateTopupAmount();
    });

    els.btnProceedTopup.addEventListener('click', proceedToPayment);

    // Modal
    els.btnCloseInstructions.addEventListener('click', hideInstructionsModal);

    // Close modal on outside click
    els.instructionsModal.addEventListener('click', (e) => {
        if (e.target === els.instructionsModal) {
            hideInstructionsModal();
        }
    });
}

function copyToClipboard(text, buttonElement) {
    // Fallback for older browsers / webview
    const textArea = document.createElement("textarea");
    textArea.value = text;

    // Avoid scrolling to bottom
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            const originalText = buttonElement.textContent;
            buttonElement.textContent = "Скопировано!";
            buttonElement.classList.replace('bg-green-500', 'bg-gray-500');
            setTimeout(() => {
                buttonElement.textContent = originalText;
                buttonElement.classList.replace('bg-gray-500', 'bg-green-500');
            }, 2000);

            // Trigger haptic feedback
            window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
        } else {
            console.error('Fallback: Copying text command was unsuccessful');
            window.Telegram.WebApp.showAlert("Не удалось скопировать.");
        }
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
        window.Telegram.WebApp.showAlert("Не удалось скопировать.");
    }

    document.body.removeChild(textArea);
}

function showInstructionsModal() {
    const html = `
        <p>🪟 <b>Windows (v2rayN / Clash)</b><br>
        Установите клиент, импортируйте ссылку из буфера обмена, обновите подписку и подключитесь.</p>

        <p>📱 <b>Android (v2rayNG)</b><br>
        Скачайте v2rayNG из Google Play, нажмите "+" -> "Импорт профиля из буфера обмена", выберите сервер и нажмите V для запуска.</p>

        <p>🍎 <b>iOS (Shadowrocket / V2Box)</b><br>
        В приложении нажмите "+" -> Type: Subscribe. Вставьте ссылку в URL, сохраните и включите VPN.</p>

        <p>🍏 <b>macOS (V2RayX / ClashX)</b><br>
        Аналогично Windows, используйте импорт по URL (Subscribe).</p>

        <p class="text-xs text-gray-500 mt-2">При проблемах с подключением обратитесь в поддержку.</p>
    `;

    els.instructionsContent.innerHTML = html;

    els.instructionsModal.classList.remove('hidden');
    // Small delay for CSS transition
    setTimeout(() => {
        els.instructionsModal.classList.remove('opacity-0');
        els.instructionsModal.children[0].classList.remove('scale-95');
    }, 10);
}

function hideInstructionsModal() {
    els.instructionsModal.classList.add('opacity-0');
    els.instructionsModal.children[0].classList.add('scale-95');

    setTimeout(() => {
        els.instructionsModal.classList.add('hidden');
    }, 300); // match transition duration
}

// Start App
document.addEventListener('DOMContentLoaded', init);
