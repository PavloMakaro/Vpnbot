const APP_ID = "YOUR_ATLAS_APP_ID"; // Replace with your real Atlas App ID later

// UI Elements
const loadingDiv = document.getElementById("loading");
const mainContent = document.getElementById("main-content");
const userGreeting = document.getElementById("user-greeting");
const userBalance = document.getElementById("user-balance");
const subStatus = document.getElementById("sub-status");
const plansContainer = document.getElementById("plans-container");
const messageContainer = document.getElementById("message-container");
const configsSection = document.getElementById("configs-section");
const configsList = document.getElementById("configs-list");
const topupBtn = document.getElementById("topup-btn");
const topupAmountInput = document.getElementById("topup-amount");

let app;

async function init() {
    try {
        const isLocal = window.location.protocol === 'file:' || window.location.hostname === 'localhost';

        // Setup mock Telegram if needed for local dev
        if (isLocal && !window.Telegram?.WebApp?.initData) {
            console.log("Setting up Mock Telegram for local development.");
            window.Telegram = {
                WebApp: {
                    initData: "mock_init_data_for_local",
                    openLink: (url) => window.open(url, '_blank')
                }
            };
        }

        const tg = window.Telegram?.WebApp;
        if (!tg || !tg.initData) {
            throw new Error("Telegram WebApp context missing.");
        }

        // Native fallback logic for mocking authentication & profile loading if local
        if (isLocal && tg.initData === "mock_init_data_for_local") {
            app = {
                currentUser: {
                    functions: {
                        getProfile: async () => ({
                            first_name: "Local",
                            username: "Dev",
                            balance: 1000,
                            subscription_end: "2030-01-01 00:00:00",
                            used_configs: [
                                { config_name: "MockConfig", config_link: "vless://mock", period: "1_month" }
                            ]
                        }),
                        getConfigs: async () => ({
                            '1_month': { price: 50, days: 30 },
                            '2_months': { price: 90, days: 60 },
                            '3_months': { price: 120, days: 90 }
                        }),
                        checkPendingPayments: async () => ({ success: true }),
                        buySubscription: async (period) => ({
                            success: true,
                            message: `Mock bought ${period}`,
                            config: { link: "vless://new_mock" },
                            new_end: "2030-02-01 00:00:00"
                        }),
                        createPayment: async (amount) => ({
                            success: true,
                            paymentId: "mock_pid_123",
                            confirmationUrl: "https://example.com/pay"
                        })
                    }
                }
            };
            console.log("Using Mock App Services.");
        } else {
            app = new Realm.App({ id: APP_ID });
            // Custom JWT auth passing initData
            const credentials = Realm.Credentials.customFunction({ initData: tg.initData });
            await app.logIn(credentials);
            console.log("Logged into Atlas App Services.");
        }

        await loadProfile();
        await loadPlans();

        loadingDiv.classList.add("hidden");
        mainContent.classList.remove("hidden");
        mainContent.classList.add("fade-in");

    } catch (err) {
        console.error("Initialization error:", err);
        loadingDiv.innerHTML = `<h2 class="text-red-500 font-bold text-xl">Error</h2><p>${err.message}</p>`;
    }
}

async function loadProfile() {
    try {
        // Sync pending payments before fetching profile
        await app.currentUser.functions.checkPendingPayments();

        const profile = await app.currentUser.functions.getProfile();
        userGreeting.innerText = `Hello, ${profile.first_name || profile.username}!`;
        userBalance.innerText = `${profile.balance || 0} ₽`;

        if (profile.subscription_end) {
            const endDate = new Date(profile.subscription_end.replace(' ', 'T'));
            if (endDate > new Date()) {
                subStatus.innerHTML = `<span class="text-green-600 font-bold">Active</span> until ${profile.subscription_end}`;
            } else {
                subStatus.innerHTML = `<span class="text-red-500 font-bold">Expired</span>`;
            }
        } else {
            subStatus.innerHTML = `<span class="text-gray-500">No active subscription</span>`;
        }

        // Render configs
        if (profile.used_configs && profile.used_configs.length > 0) {
            configsSection.classList.remove("hidden");
            configsList.innerHTML = profile.used_configs.map(cfg => `
                <li class="border-b pb-2 mb-2">
                    <p class="font-bold">${cfg.config_name} (${cfg.period})</p>
                    <p class="text-sm text-blue-500 break-all cursor-pointer" onclick="copyToClipboard('${cfg.config_link}')">${cfg.config_link}</p>
                    <p class="text-xs text-gray-400">Click link to copy</p>
                </li>
            `).join('');
        }

    } catch (err) {
        console.error("Failed to load profile", err);
        showMessage("Failed to load profile.", "red");
    }
}

async function loadPlans() {
    try {
        const plans = await app.currentUser.functions.getConfigs();
        plansContainer.innerHTML = Object.entries(plans).map(([key, data]) => `
            <div class="flex justify-between items-center p-3 border rounded hover:bg-gray-50 transition">
                <div>
                    <p class="font-bold">${data.days} Days</p>
                    <p class="text-gray-500">${data.price} ₽</p>
                </div>
                <button onclick="buySubscription('${key}')" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 font-bold">Buy</button>
            </div>
        `).join('');
    } catch (err) {
        console.error("Failed to load plans", err);
    }
}

async function buySubscription(period) {
    if(!confirm(`Buy subscription for ${period}?`)) return;

    showMessage("Processing purchase...", "blue");
    try {
        const res = await app.currentUser.functions.buySubscription(period);
        if (res.success) {
            showMessage("Subscription purchased successfully!", "green");
            await loadProfile(); // Refresh UI
            if(res.config && res.config.link) {
                 // In a real app, you might want to show a modal with the link
                 console.log("New config:", res.config.link);
            }
        } else {
            showMessage(`Failed: ${res.message}`, "red");
        }
    } catch (err) {
        console.error(err);
        showMessage("An error occurred during purchase.", "red");
    }
}

topupBtn.addEventListener("click", async () => {
    const amount = parseInt(topupAmountInput.value);
    if (isNaN(amount) || amount < 50) {
        showMessage("Minimum topup is 50 RUB.", "red");
        return;
    }

    showMessage("Creating payment...", "blue");
    try {
        const returnUrl = window.location.href;
        const res = await app.currentUser.functions.createPayment(amount, returnUrl);
        if (res.success && res.confirmationUrl) {
            if (window.Telegram?.WebApp) {
                 window.Telegram.WebApp.openLink(res.confirmationUrl);
            } else {
                 window.open(res.confirmationUrl, '_blank');
            }
            showMessage("Redirecting to payment...", "green");

            // Periodically check payment status
            const checkInterval = setInterval(async () => {
                const checkRes = await app.currentUser.functions.checkPendingPayments();
                await loadProfile(); // Refresh balance if updated
                // We don't stop interval easily here without keeping track of specific pending payments,
                // but for a simple SPA, calling loadProfile() occasionally while page is open works.
            }, 10000);

            // Clear interval after 5 mins to prevent infinite checking
            setTimeout(() => clearInterval(checkInterval), 300000);

        } else {
            showMessage(`Payment creation failed: ${res.message}`, "red");
        }
    } catch (err) {
        console.error(err);
        showMessage("An error occurred creating payment.", "red");
    }
});

function showMessage(msg, color) {
    messageContainer.innerHTML = `<span class="text-${color}-600">${msg}</span>`;
    setTimeout(() => { messageContainer.innerHTML = ''; }, 5000);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showMessage("Link copied to clipboard!", "green");
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}

// Initialize the app on load
window.addEventListener('DOMContentLoaded', init);
