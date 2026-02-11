// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Initialize Realm App
// REPLACE WITH YOUR REALM APP ID
const app = new Realm.App({ id: "vpn-bot-xxxxx" });

// State
let currentUser = null;
let userProfile = null;
let plans = [];

async function init() {
    try {
        // Authenticate using Telegram InitData
        const credentials = Realm.Credentials.function({
            initData: tg.initData
        });

        currentUser = await app.logIn(credentials);
        console.log("Logged in:", currentUser.id);

        // Fetch User Profile
        userProfile = await currentUser.functions.getUserProfile();
        updateUI();

        // Fetch Plans
        plans = await currentUser.functions.getPlans();
        renderPlans();

        document.getElementById("loading").classList.add("hidden");
        document.getElementById("app").classList.remove("hidden");

    } catch (err) {
        console.error("Failed to log in", err);
        tg.showAlert("Authentication failed. Please restart the bot.");
    }
}

function updateUI() {
    if (!userProfile) return;

    document.getElementById("user-name").innerText = userProfile.first_name || "User";
    document.getElementById("user-balance").innerText = userProfile.balance || 0;

    // Avatar
    const avatarEl = document.getElementById("user-avatar");
    const initialsEl = document.getElementById("user-initials");

    if (tg.initDataUnsafe?.user?.photo_url) {
        avatarEl.src = tg.initDataUnsafe.user.photo_url;
        avatarEl.classList.remove("hidden");
        initialsEl.classList.add("hidden");
    } else {
        initialsEl.innerText = (userProfile.first_name || "U").charAt(0).toUpperCase();
        avatarEl.classList.add("hidden");
        initialsEl.classList.remove("hidden");
    }

    // Subscription Status
    const subText = document.getElementById("sub-text");
    if (userProfile.active_subscription) {
        const endDate = new Date(userProfile.subscription_end).toLocaleDateString();
        subText.innerText = `Active until ${endDate}`;
        subText.classList.add("text-green-600");
    } else {
        subText.innerText = "No active subscription";
        subText.classList.add("text-red-500");
    }
}

function showView(viewName) {
    document.getElementById("app").classList.add("hidden");
    document.querySelectorAll(".view").forEach(el => el.classList.add("hidden"));

    const view = document.getElementById(`view-${viewName}`);
    if (view) {
        view.classList.remove("hidden");

        if (viewName === 'my-configs') {
            loadConfigs();
        }
    }
}

function goBack() {
    document.querySelectorAll(".view").forEach(el => el.classList.add("hidden"));
    document.getElementById("app").classList.remove("hidden");
}

function renderPlans() {
    const container = document.getElementById("plans-container");
    container.innerHTML = "";

    plans.forEach(plan => {
        const div = document.createElement("div");
        div.className = "card p-4 rounded-lg flex justify-between items-center";
        div.innerHTML = `
            <div>
                <h3 class="font-bold text-lg">${plan.days} Days</h3>
                <p class="text-sm opacity-70">${plan.price} RUB</p>
            </div>
            <button onclick="buySubscription('${plan._id}')" class="btn-primary px-4 py-2 rounded-lg font-medium">Buy</button>
        `;
        container.appendChild(div);
    });
}

async function buySubscription(planId) {
    if (!confirm("Are you sure you want to buy this subscription?")) return;

    tg.MainButton.showProgress();
    try {
        const result = await currentUser.functions.buySubscription(planId);
        if (result.success) {
            tg.showAlert("Subscription purchased successfully!");
            // Refresh Profile
            userProfile = await currentUser.functions.getUserProfile();
            updateUI();
            goBack();
        }
    } catch (err) {
        console.error(err);
        tg.showAlert("Error: " + err.message);
    } finally {
        tg.MainButton.hideProgress();
    }
}

async function initiatePayment() {
    const amount = parseFloat(document.getElementById("topup-amount").value);
    if (!amount || amount < 50) {
        tg.showAlert("Minimum amount is 50 RUB");
        return;
    }

    tg.MainButton.showProgress();
    try {
        const result = await currentUser.functions.createPayment(amount);
        if (result.payment_url) {
            tg.openLink(result.payment_url);
        }
    } catch (err) {
        console.error(err);
        tg.showAlert("Error creating payment: " + err.message);
    } finally {
        tg.MainButton.hideProgress();
    }
}

async function loadConfigs() {
    const container = document.getElementById("configs-container");
    container.innerHTML = "<p>Loading...</p>";

    try {
        const configs = await currentUser.functions.getMyConfigs();
        container.innerHTML = "";

        if (configs.length === 0) {
            container.innerHTML = "<p class='opacity-70 text-center'>No configs found.</p>";
            return;
        }

        configs.forEach(config => {
            const div = document.createElement("div");
            div.className = "card p-4 rounded-lg space-y-2";
            div.innerHTML = `
                <h3 class="font-bold">${config.config_name}</h3>
                <p class="text-xs opacity-70">Issued: ${new Date(config.issue_date).toLocaleDateString()}</p>
                <div class="bg-gray-200 p-2 rounded text-xs break-all font-mono select-all">
                    ${config.config_link}
                </div>
                <button class="w-full text-center text-blue-500 text-sm" onclick="copyToClipboard('${config.config_link}')">Copy Link</button>
            `;
            container.appendChild(div);
        });
    } catch (err) {
        console.error(err);
        container.innerHTML = "<p class='text-red-500'>Failed to load configs.</p>";
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        tg.showAlert("Copied to clipboard!");
    }).catch(err => {
        console.error('Async: Could not copy text: ', err);
    });
}

// Start
init();
