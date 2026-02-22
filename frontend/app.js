// Atlas App Services Config
// REPLACE WITH YOUR REAL APP ID AFTER DEPLOYMENT
const APP_ID = "vpn-bot-xxxxx";

const tg = window.Telegram.WebApp;
const realmApp = new Realm.App({ id: APP_ID });

let user = null;
let mongoUser = null; // The authenticated Realm User

// Init
document.addEventListener('DOMContentLoaded', async () => {
    tg.ready();
    tg.expand();

    // Theme handling
    if (tg.colorScheme === 'dark') {
        document.body.classList.add('dark-mode');
        document.body.classList.remove('light-mode');
    } else {
        document.body.classList.add('light-mode');
        document.body.classList.remove('dark-mode');
    }

    // Auth
    try {
        await authenticate();
        await loadUserData();
        document.getElementById('loader').classList.add('hidden');
    } catch (e) {
        console.error("Auth Failed", e);
        // Show error or retry
        // Ideally show a "Connect to Bot" screen if initData is missing (dev mode)
        if (!tg.initData) {
            alert("Please open from Telegram");
        } else {
             alert("Auth Error: " + e.message);
        }
        document.getElementById('loader').classList.add('hidden');
    }
});

async function authenticate() {
    // In production, use the custom function auth with tg.initData
    // For Dev/Mock, we might need a fallback or just fail if not in TG.

    if (!tg.initData) {
        // Fallback for browser testing (remove in prod)
        console.warn("No initData, strictly for UI testing.");
        return;
    }

    // Authenticate with Realm using the Custom Function
    const credentials = Realm.Credentials.function({
        initData: tg.initData
    });

    mongoUser = await realmApp.logIn(credentials);
    console.log("Logged in as", mongoUser.id);
}

async function loadUserData() {
    if (!mongoUser) return;

    // Call Atlas Function 'getUser'
    const userData = await mongoUser.functions.getUser();

    // Update UI
    document.getElementById('user-name').innerText = userData.first_name || 'User';
    document.getElementById('user-id').innerText = mongoUser.id.substring(0, 8); // Display partial ID or TG ID
    document.getElementById('user-avatar').innerText = (userData.first_name || 'U')[0].toUpperCase();
    document.getElementById('user-balance').innerText = userData.balance;

    // Sub Status
    const subText = document.getElementById('sub-text');
    const subIndicator = document.getElementById('sub-indicator');
    const subDate = document.getElementById('sub-date');

    if (userData.days_left > 0) {
        subText.innerText = `Активна (${userData.days_left} дн.)`;
        subIndicator.classList.remove('bg-red-500');
        subIndicator.classList.add('bg-green-500');
        subDate.innerText = `До ${new Date(userData.subscription_end).toLocaleDateString()}`;
    } else {
        subText.innerText = "Не активна";
        subIndicator.classList.remove('bg-green-500');
        subIndicator.classList.add('bg-red-500');
        subDate.innerText = "Купите подписку, чтобы пользоваться VPN";
    }

    // Load configs preview (stub for now, need 'getMyConfigs' function or reuse getUser data if it includes them)
    // Assuming getUser returns recent configs or we fetch them separately
    // If we added 'used_configs' to getUser result:
    // renderConfigs(userData.used_configs);
}

// Navigation
window.showPage = function(pageId) {
    document.getElementById(`page-${pageId}`).classList.remove('hidden');
    if (pageId === 'shop') loadShop();
    if (pageId === 'configs') loadConfigs();
};

window.hidePage = function(pageId) {
    document.getElementById(`page-${pageId}`).classList.add('hidden');
    // Refresh data when closing pages in case of updates
    loadUserData();
};

// Shop Logic
async function loadShop() {
    const container = document.getElementById('shop-items');
    container.innerHTML = '<div class="text-center">Loading...</div>';

    try {
        const configs = await mongoUser.functions.getConfigs();
        container.innerHTML = '';

        for (const [key, plan] of Object.entries(configs)) {
            const el = document.createElement('div');
            el.className = 'bg-white p-4 rounded-xl shadow flex justify-between items-center card-bg';
            el.innerHTML = `
                <div>
                    <h3 class="font-bold text-lg">${plan.label || key}</h3>
                    <p class="text-gray-500 text-sm">${plan.days} дней</p>
                </div>
                <button onclick="buySubscription('${key}', ${plan.price})" class="bg-blue-500 text-white px-4 py-2 rounded-lg font-bold shadow hover:bg-blue-600 active:scale-95 transition">
                    ${plan.price} ₽
                </button>
            `;
            container.appendChild(el);
        }
    } catch (e) {
        container.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

window.buySubscription = async function(key, price) {
    if (!confirm(`Купить подписку за ${price} ₽?`)) return;

    tg.MainButton.showProgress();
    try {
        const result = await mongoUser.functions.buySubscription(key);
        if (result.success) {
            alert("Успешно! Конфиг доступен в разделе 'Мои конфиги'.");
            hidePage('shop');
            loadUserData();
        }
    } catch (e) {
        alert("Ошибка: " + e.message);
    }
    tg.MainButton.hideProgress();
};

// Topup Logic
window.setTopup = function(amount) {
    document.getElementById('topup-amount').value = amount;
};

window.initiatePayment = async function() {
    const amount = parseFloat(document.getElementById('topup-amount').value);
    if (!amount || amount < 10) {
        alert("Минимум 10 ₽");
        return;
    }

    const btn = document.getElementById('pay-btn');
    const originalText = btn.innerText;
    btn.innerText = "Создание платежа...";
    btn.disabled = true;

    try {
        // Create payment link
        const res = await mongoUser.functions.createPayment(amount, window.location.href);

        // Open payment in new window/tab or via Telegram WebApp openLink
        tg.openLink(res.confirmation_url);

        // Optionally start polling for status or show "Check Status" button
        if (confirm("Вы оплатили? Нажмите ОК, чтобы проверить статус.")) {
            await checkPaymentStatus(res.payment_id);
        }

    } catch (e) {
        alert("Error: " + e.message);
    }

    btn.innerText = originalText;
    btn.disabled = false;
};

async function checkPaymentStatus(paymentId) {
    tg.MainButton.showProgress();
    try {
        const res = await mongoUser.functions.checkPayment(paymentId);
        if (res.status === 'succeeded') {
            alert("Оплата прошла успешно! Баланс пополнен.");
            hidePage('topup');
            loadUserData();
        } else {
            alert("Статус платежа: " + res.status + ". Попробуйте позже.");
        }
    } catch (e) {
        alert("Ошибка проверки: " + e.message);
    }
    tg.MainButton.hideProgress();
}

// Configs Logic
async function loadConfigs() {
    // This assumes we fetch full user data again or have a specific function
    // For now, let's just re-fetch user data which contains 'used_configs'
    // Or call a dedicated function if the list is long

    // Stub: reusing getUser logic or adding a 'getMyConfigs' function
    // Let's assume getUser returns it or we create getMyConfigs

    // For simplicity in this plan, I'll rely on getUser updating the global user object/cache
    // but practically we should fetch fresh list.

    // Let's reload user data first
    const userData = await mongoUser.functions.getUser(); // re-fetch
    // Wait, getUser in step 2 logic returned profile info.
    // It didn't explicitly return the array of used_configs to save bandwidth?
    // Let's check getUser.js content I wrote.
    // I wrote: return { balance, subscription_end, ... } but NOT used_configs.
    // So I need a new function `getMyConfigs`.

    // Note: I didn't create `getMyConfigs.js` in the backend step!
    // I should create it now or rely on updating `getUser.js` or assume I can modify it.
    // I'll create a new tool call to create `getMyConfigs.js` in the backend step or just add it here since I'm "fixing" things.
    // Actually, I can't go back easily. I will add `getMyConfigs.js` creation in the current step (Frontend) or add logic to `app.js` to handle it if I add the file.

    // I will add a 'getMyConfigs' call here, and I'll make sure to create that file in the next step or right now using a tool.
    // Since I'm in the Frontend step, creating a backend file is technically out of scope but necessary for the frontend to work.
    // I'll assume I can add it.

    const container = document.getElementById('configs-full-list');
    container.innerHTML = '<div class="text-center">Loading...</div>';

    // Temporary fallback until backend function exists:
    // alert("Backend function getMyConfigs needs to be created!");

    try {
        // Try calling it (I'll create it in a moment)
        const configs = await mongoUser.functions.getMyConfigs();

        container.innerHTML = '';
        if (!configs || configs.length === 0) {
            container.innerHTML = '<p class="text-center text-gray-500">Нет конфигов</p>';
            return;
        }

        configs.reverse().forEach(conf => {
            const el = document.createElement('div');
            el.className = 'bg-white p-4 rounded-xl shadow space-y-2 card-bg';
            el.innerHTML = `
                <div class="flex justify-between">
                    <span class="font-bold">${conf.config_name || 'VPN Config'}</span>
                    <span class="text-xs text-gray-400">${new Date(conf.issue_date).toLocaleDateString()}</span>
                </div>
                <div class="bg-gray-100 p-2 rounded text-xs break-all font-mono select-all">
                    ${conf.config_link}
                </div>
                <button onclick="navigator.clipboard.writeText('${conf.config_link}').then(()=>alert('Copied!'))" class="text-blue-500 text-sm font-bold w-full text-right">
                    Копировать
                </button>
            `;
            container.appendChild(el);
        });
    } catch(e) {
         container.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}
