// CONFIGURATION - REPLACE WITH YOUR REALM APP ID
const REALM_APP_ID = "vpn-bot-xxxxx";

const tg = window.Telegram.WebApp;
const realmApp = new Realm.App({ id: REALM_APP_ID });

const app = {
    user: null,
    realmUser: null,

    init: async () => {
        try {
            tg.ready();
            tg.expand();

            // Set theme colors
            document.documentElement.style.setProperty('--tg-theme-bg-color', tg.backgroundColor || '#1a1a1a');
            document.documentElement.style.setProperty('--tg-theme-text-color', tg.textColor || '#ffffff');
            document.documentElement.style.setProperty('--tg-theme-button-color', tg.buttonColor || '#3b82f6');
            document.documentElement.style.setProperty('--tg-theme-button-text-color', tg.buttonTextColor || '#ffffff');
            document.documentElement.style.setProperty('--tg-theme-secondary-bg-color', tg.secondaryBackgroundColor || '#2d2d2d');

            // Login using Custom Function Authentication
            const credentials = Realm.Credentials.function({ initData: tg.initData });
            app.realmUser = await realmApp.logIn(credentials);

            // Fetch User Profile
            await app.refreshUserData();

            // Hide loading screen
            document.getElementById('loading-screen').classList.add('hidden');
            app.switchTab('home');

        } catch (error) {
            console.error("Init error:", error);
            document.getElementById('loading-screen').innerHTML = `<div class="text-red-500 p-4 text-center">Ошибка инициализации: ${error.message}<br>Проверьте APP_ID в app.js</div>`;
        }
    },

    // UI RENDERING
    renderAll: () => {
        if (!app.user) return;
        app.renderHome();
        app.renderConfigs();
        app.renderProfile();
    },

    renderHome: () => {
        document.getElementById('user-balance').innerText = app.user.balance;

        const subStatus = document.getElementById('sub-status-badge');
        const subDetails = document.getElementById('sub-details');
        const subExpiry = document.getElementById('sub-expiry');
        const subDate = document.getElementById('sub-date');

        const now = new Date();
        const subEnd = app.user.subscription_end ? new Date(app.user.subscription_end) : null;

        if (subEnd && subEnd > now) {
            const daysLeft = Math.ceil((subEnd - now) / (1000 * 60 * 60 * 24));
            subStatus.innerText = `Активна (${daysLeft} дн.)`;
            subStatus.classList.remove('bg-gray-600');
            subStatus.classList.add('bg-green-600');

            subDetails.innerText = "VPN Подключен";
            subExpiry.classList.remove('hidden');
            subDate.innerText = subEnd.toLocaleDateString();
        } else {
            subStatus.innerText = "Неактивна";
            subStatus.classList.remove('bg-green-600');
            subStatus.classList.add('bg-gray-600');

            subDetails.innerText = "Нет активной подписки";
            subExpiry.classList.add('hidden');
        }
    },

    renderConfigs: () => {
        const list = document.getElementById('configs-list');
        list.innerHTML = '';

        if (!app.user.used_configs || app.user.used_configs.length === 0) {
            list.innerHTML = '<div class="text-center text-hint py-8">Нет активных конфигов</div>';
            return;
        }

        app.user.used_configs.forEach((conf, index) => {
            const item = document.createElement('div');
            item.className = 'card p-4 rounded-xl shadow-sm flex flex-col gap-2';
            item.innerHTML = `
                <div class="flex justify-between items-start">
                    <div class="font-bold text-lg">${conf.config_name || 'Config #' + (index + 1)}</div>
                    <span class="text-xs bg-gray-700 px-2 py-1 rounded">${conf.period}</span>
                </div>
                <div class="text-xs text-hint">Выдан: ${conf.issue_date}</div>
                <div class="bg-[var(--tg-theme-bg-color)] p-2 rounded text-xs break-all font-mono select-all overflow-hidden max-h-20">
                    ${conf.config_link}
                </div>
                <button onclick="navigator.clipboard.writeText('${conf.config_link}').then(() => tg.showAlert('Скопировано!'))" class="text-sm text-blue-400 font-medium self-end">
                    <i class="fas fa-copy"></i> Копировать
                </button>
            `;
            list.appendChild(item);
        });
    },

    renderProfile: () => {
        document.getElementById('profile-name').innerText = app.user.first_name;
        document.getElementById('profile-username').innerText = app.user.username ? '@' + app.user.username : 'ID: ' + app.user._id;
        document.getElementById('profile-avatar').innerText = app.user.first_name.charAt(0);

        const refCount = app.user.referral ? app.user.referral.count : 0;
        const refEarnings = refCount * 25; // 25 rub per referral

        document.getElementById('ref-count').innerText = refCount;
        document.getElementById('ref-earnings').innerText = refEarnings + ' ₽';

        document.getElementById('ref-link').value = `https://t.me/${window.BOT_USERNAME || 'vpni50_bot'}?start=${app.user._id}`;
    },

    // NAVIGATION
    switchTab: (tabId) => {
        document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
        document.getElementById('view-' + tabId).classList.remove('hidden');

        document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
        document.querySelector(`.nav-btn[data-tab="${tabId}"]`).classList.add('active');

        if (tabId === 'configs' || tabId === 'profile') {
            app.refreshUserData();
        }
    },

    // MODALS
    openTopUpModal: () => {
        document.getElementById('modal-topup').classList.remove('hidden');
    },

    openBuySubscription: () => {
        document.getElementById('modal-buy').classList.remove('hidden');
    },

    closeModal: (modalId) => {
        document.getElementById(modalId).classList.add('hidden');
    },

    // LOGIC
    refreshUserData: async () => {
        try {
            const res = await app.realmUser.functions.getUser();
            if (res.user) {
                app.user = res.user;
                app.renderAll();
            } else if (res.error) {
                console.error(res.error);
            }
        } catch (e) {
            console.error(e);
        }
    },

    selectTopUpAmount: (amount) => {
        document.getElementById('custom-amount').value = amount;
    },

    initiatePayment: async () => {
        const amount = parseInt(document.getElementById('custom-amount').value);
        if (!amount || amount < 10) {
            tg.showAlert("Минимальная сумма: 10 ₽");
            return;
        }

        tg.MainButton.showProgress();
        try {
            const res = await app.realmUser.functions.createPayment(amount);
            tg.MainButton.hideProgress();

            if (res.confirmation_url) {
                tg.openLink(res.confirmation_url);
                app.closeModal('modal-topup');
                tg.showAlert("Платеж создан. После оплаты баланс обновится автоматически.");
            } else {
                tg.showAlert("Ошибка создания платежа: " + res.error);
            }
        } catch (e) {
            tg.MainButton.hideProgress();
            tg.showAlert("Ошибка: " + e.message);
        }
    },

    selectPlan: async (period, price) => {
        if (app.user.balance < price) {
            tg.showConfirm(`Недостаточно средств. Пополнить на ${price - app.user.balance} ₽?`, (ok) => {
                if (ok) {
                    app.closeModal('modal-buy');
                    app.openTopUpModal();
                    app.selectTopUpAmount(price - app.user.balance);
                }
            });
            return;
        }

        tg.MainButton.setText(`Купить за ${price} ₽`);
        tg.MainButton.show();

        tg.MainButton.onClick(async () => {
            tg.MainButton.showProgress();
            try {
                const res = await app.realmUser.functions.buySubscription(period);
                tg.MainButton.hideProgress();
                tg.MainButton.hide();

                if (res.success) {
                    app.user = res.user; // Update user with response
                    app.renderAll();
                    app.closeModal('modal-buy');
                    app.switchTab('configs');
                    tg.showAlert("Подписка успешно оформлена! Ваш конфиг готов.");
                } else {
                    tg.showAlert("Ошибка: " + res.error);
                }
            } catch (e) {
                tg.MainButton.hideProgress();
                tg.MainButton.hide();
                tg.showAlert("Ошибка: " + e.message);
            }
        });
    },

    copyRefLink: () => {
        const link = document.getElementById('ref-link').value;
        navigator.clipboard.writeText(link).then(() => {
            tg.showAlert("Ссылка скопирована!");
        });
    },

    openSupport: () => {
        tg.openTelegramLink("https://t.me/Gl1ch555");
    }
};

// Initialize app
window.onload = app.init;
