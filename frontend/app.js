const APP_ID = "YOUR_ATLAS_APP_ID"; // Replace with your actual App ID
const app = new Realm.App({ id: APP_ID });

let currentUser = null;
let selectedTopupAmount = null;

// Mock data for local testing
const mockProfile = {
    id: "123456789",
    username: "testuser",
    first_name: "Test",
    balance: 500,
    subscription_end: "2024-12-31 23:59:59",
    referrals_count: 5,
    used_configs: [
        {
            config_name: "Config_1_month_1",
            config_link: "vless://mock-link-1",
            period: "1_month",
            issue_date: "2024-01-01 12:00:00"
        }
    ]
};

const mockConfigs = {
    subscription_periods: {
        '1_month': { price: 50, days: 30 },
        '2_months': { price: 90, days: 60 },
        '3_months': { price: 120, days: 90 }
    },
    used_configs: mockProfile.used_configs
};

// Initialize app
document.addEventListener("DOMContentLoaded", async () => {
    try {
        window.Telegram.WebApp.expand();
        const initData = window.Telegram.WebApp.initData;

        if (!initData) {
            // Local mockup fallback
            if (window.location.protocol === "file:" || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
                console.log("Running locally, using mock authentication.");
                await loadDashboard(mockProfile, mockConfigs);
                return;
            }
            throw new Error("Telegram initData is missing. Open this app from Telegram.");
        }

        // Authenticate with Realm using Custom Function
        const credentials = Realm.Credentials.function({ initData });
        currentUser = await app.logIn(credentials);

        // Fetch data
        const profile = await currentUser.functions.getProfile();
        const configs = await currentUser.functions.getConfigs();

        await loadDashboard(profile, configs);

    } catch (err) {
        showError(err.message);
    }
});

async function loadDashboard(profile, configs) {
    document.getElementById("userName").textContent = profile.first_name || profile.username || "User";
    document.getElementById("userId").textContent = `ID: ${profile.id}`;
    document.getElementById("userBalance").textContent = `${profile.balance} ₽`;
    document.getElementById("buyTabBalance").textContent = `${profile.balance} ₽`;
    document.getElementById("topupTabBalance").textContent = `${profile.balance} ₽`;

    if (profile.subscription_end) {
        const endDate = new Date(profile.subscription_end.replace(' ', 'T'));
        const now = new Date();
        if (endDate > now) {
            const daysLeft = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));
            document.getElementById("userSubscription").textContent = `Active: ${daysLeft} days left`;
            document.getElementById("userSubscription").className = "text-green-600 font-bold text-sm";
        } else {
            document.getElementById("userSubscription").textContent = "Expired";
            document.getElementById("userSubscription").className = "text-red-500 font-bold text-sm";
        }
    } else {
         document.getElementById("userSubscription").textContent = "No active sub";
         document.getElementById("userSubscription").className = "text-gray-500 font-bold text-sm";
    }

    renderConfigs(configs.used_configs);
    renderSubscriptionPlans(configs.subscription_periods);

    document.getElementById("loadingView").classList.add("hidden-view");
    document.getElementById("mainView").classList.remove("hidden-view");
    document.getElementById("bottomNav").classList.remove("hidden-view");
}

function renderConfigs(configsList) {
    const listEl = document.getElementById("configsList");
    const noMsg = document.getElementById("noConfigsMsg");
    listEl.innerHTML = "";

    if (!configsList || configsList.length === 0) {
        noMsg.classList.remove("hidden");
        return;
    }

    noMsg.classList.add("hidden");

    configsList.forEach(config => {
        const div = document.createElement("div");
        div.className = "bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex justify-between items-center";

        let periodText = config.period.replace('_', ' ');

        div.innerHTML = `
            <div>
                <h4 class="font-bold text-gray-800">${config.config_name || "VPN Config"}</h4>
                <p class="text-xs text-gray-500">${periodText} • ${config.issue_date}</p>
            </div>
            <button onclick="copyToClipboard('${config.config_link}')" class="bg-gray-100 p-2 rounded-lg text-blue-500 active:bg-blue-100 transition">
                Copy
            </button>
        `;
        listEl.appendChild(div);
    });
}

function renderSubscriptionPlans(periods) {
    const plansEl = document.getElementById("subscriptionPlans");
    plansEl.innerHTML = "";

    for (const [key, data] of Object.entries(periods)) {
        const div = document.createElement("div");
        div.className = "bg-white border border-gray-200 p-4 rounded-xl flex justify-between items-center";
        div.innerHTML = `
            <div>
                <h3 class="font-bold text-lg">${data.days} Days</h3>
                <p class="text-blue-500 font-bold">${data.price} ₽</p>
            </div>
            <button onclick="buySubscription('${key}')" class="btn-primary px-4 py-2 rounded-lg font-medium shadow-sm active:opacity-80">
                Buy
            </button>
        `;
        plansEl.appendChild(div);
    }
}

function showTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden-view"));
    document.getElementById(tabId).classList.remove("hidden-view");
    document.getElementById(tabId).classList.add("fade-in");
    window.scrollTo(0, 0);
}

function selectTopupAmount(amount) {
    document.getElementById("customAmount").value = amount;
    selectedTopupAmount = amount;
}

async function processTopup() {
    const amountInput = document.getElementById("customAmount").value;
    const amount = parseInt(amountInput);

    if (isNaN(amount) || amount < 50) {
        window.Telegram.WebApp.showAlert("Minimum top up amount is 50 ₽");
        return;
    }

    if (!currentUser) {
        window.Telegram.WebApp.showAlert("Mock: Payment initiated for " + amount + " ₽");
        return;
    }

    try {
        const btn = document.querySelector("#tabTopup .btn-primary");
        const originalText = btn.textContent;
        btn.textContent = "Creating payment...";
        btn.disabled = true;

        const result = await currentUser.functions.createPayment(
            amount,
            `Top up balance for ${amount} ₽`,
            "https://t.me/YOUR_BOT_USERNAME" // REPLACE THIS
        );

        if (result && result.confirmation_url) {
            window.Telegram.WebApp.openLink(result.confirmation_url);
            // In a real app, you'd want to poll for payment status or wait for webhook
            window.Telegram.WebApp.showAlert("Please complete payment in browser. Once done, reload the app.");
        } else {
             window.Telegram.WebApp.showAlert("Error creating payment.");
        }

        btn.textContent = originalText;
        btn.disabled = false;

    } catch (err) {
        window.Telegram.WebApp.showAlert("Payment Error: " + err.message);
    }
}

async function buySubscription(periodKey) {
    window.Telegram.WebApp.showConfirm("Are you sure you want to buy this subscription?", async (confirmed) => {
        if (!confirmed) return;

        if (!currentUser) {
            window.Telegram.WebApp.showAlert("Mock: Bought " + periodKey);
            return;
        }

        try {
            document.getElementById("loadingText").textContent = "Processing...";
            document.getElementById("loadingView").classList.remove("hidden-view");

            const result = await currentUser.functions.buySubscription(periodKey);

            document.getElementById("loadingView").classList.add("hidden-view");

            if (result.success) {
                window.Telegram.WebApp.showAlert("Subscription purchased successfully!");
                // Refresh data
                const profile = await currentUser.functions.getProfile();
                const configs = await currentUser.functions.getConfigs();
                await loadDashboard(profile, configs);
                showTab('tabDashboard');
            } else {
                window.Telegram.WebApp.showAlert("Error: " + result.error);
            }

        } catch (err) {
            document.getElementById("loadingView").classList.add("hidden-view");
            window.Telegram.WebApp.showAlert("Purchase Error: " + err.message);
        }
    });
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            window.Telegram.WebApp.showAlert("Copied to clipboard!");
        }).catch(err => {
            console.error('Failed to copy', err);
        });
    } else {
        // Fallback
        const textArea = document.createElement("textarea");
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            window.Telegram.WebApp.showAlert("Copied to clipboard!");
        } catch (err) {
            console.error('Fallback copy failed', err);
        }
        document.body.removeChild(textArea);
    }
}

function showError(msg) {
    document.getElementById("loadingView").classList.add("hidden-view");
    document.getElementById("mainView").classList.add("hidden-view");
    document.getElementById("bottomNav").classList.add("hidden-view");
    document.getElementById("errorView").classList.remove("hidden-view");
    document.getElementById("errorMessage").textContent = msg;
}