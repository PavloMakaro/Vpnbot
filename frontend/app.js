const app = new Realm.App({ id: "application-0-your-id" }); // REPLACE WITH YOUR ATLAS APP ID

let currentUser;

document.addEventListener("DOMContentLoaded", async () => {
    try {
        if (!window.Telegram || !window.Telegram.WebApp) {
            console.error("Telegram WebApp API not found.");
            // In a real environment, you might mock or show an error
        } else {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }

        // Mock initData for testing outside Telegram (if needed)
        const initData = window.Telegram?.WebApp?.initData || "mockInitData";

        // Custom JWT logic (using Custom Function Auth)
        const credentials = Realm.Credentials.function({ initData });
        currentUser = await app.logIn(credentials);

        console.log("Logged in successfully:", currentUser.id);

        await initializeDashboard();
    } catch (err) {
        console.error("Authentication failed:", err);
        document.getElementById("loading").innerHTML = `<p class="text-red-500 font-bold p-4 text-center">Authentication Error: ${err.message}</p>`;
    }
});

async function initializeDashboard() {
    try {
        // Fetch Profile
        const profile = await currentUser.functions.getProfile();
        updateProfileUI(profile);

        // Fetch Configs (Prices)
        const configs = await currentUser.functions.getConfigs();
        renderPlans(configs);

        // Render My Configs
        renderMyConfigs(profile.used_configs);

        // Check for pending payments (instead of relying on URL parameters)
        await checkPendingPayments();

        // Show Content
        document.getElementById("loading").classList.add("hidden");
        document.getElementById("content").classList.remove("hidden");
        document.getElementById("content").classList.add("slide-up");

        setupEventListeners();

    } catch (err) {
        console.error("Failed to initialize dashboard:", err);
        document.getElementById("loading").innerHTML = `<p class="text-red-500 font-bold p-4 text-center">Error loading data.</p>`;
    }
}

function updateProfileUI(profile) {
    document.getElementById("userName").textContent = profile.first_name || profile.username || "User";
    document.getElementById("userBalance").textContent = profile.balance || 0;

    let subText = "No active subscription";
    if (profile.subscription_end) {
        // Handle Safari Date parsing issue
        const dateStr = typeof profile.subscription_end === 'string' ? profile.subscription_end.replace(' ', 'T') : profile.subscription_end;
        const subDate = new Date(dateStr);
        if (subDate > new Date()) {
            subText = `Active until ${subDate.toLocaleDateString()}`;
        }
    }
    document.getElementById("userSub").textContent = subText;
}

function renderPlans(configs) {
    const plansList = document.getElementById("plansList");
    plansList.innerHTML = "";

    for (const [period, data] of Object.entries(configs)) {
        const div = document.createElement("div");
        div.className = "flex justify-between items-center p-4 bg-white border border-gray-200 rounded-lg shadow-sm plan-card cursor-pointer";
        div.innerHTML = `
            <div>
                <p class="font-bold text-gray-800">${data.days} Days</p>
                <p class="text-sm text-gray-500">${data.price} RUB</p>
            </div>
            <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm transition" onclick="buySubscription('${period}', ${data.price})">Buy</button>
        `;
        plansList.appendChild(div);
    }
}

function renderMyConfigs(usedConfigs) {
    const myConfigsList = document.getElementById("myConfigsList");
    myConfigsList.innerHTML = "";

    if (!usedConfigs || usedConfigs.length === 0) {
        myConfigsList.innerHTML = `<p class="text-gray-500 text-sm">You don't have any configurations yet.</p>`;
        return;
    }

    usedConfigs.forEach(config => {
        const div = document.createElement("div");
        div.className = "config-card mb-3";
        const dateStr = typeof config.issue_date === 'string' ? config.issue_date.replace(' ', 'T') : config.issue_date;
        const issueDate = new Date(dateStr).toLocaleDateString();
        div.innerHTML = `
            <p class="font-semibold text-gray-800">${config.config_name}</p>
            <p class="text-xs text-gray-500 mb-2">Issued: ${issueDate} | Period: ${config.period}</p>
            <div class="flex items-center justify-between bg-white border p-2 rounded">
                <code class="text-xs truncate w-3/4">${config.config_link}</code>
                <button onclick="copyToClipboard('${config.config_link}')" class="text-blue-600 text-xs font-bold px-2 py-1 rounded border border-blue-600 hover:bg-blue-50">Copy</button>
            </div>
        `;
        myConfigsList.appendChild(div);
    });
}

function setupEventListeners() {
    const topupBtn = document.getElementById("topupBtn");
    const modal = document.getElementById("topupModal");
    const cancelBtn = document.getElementById("cancelTopup");
    const confirmBtn = document.getElementById("confirmTopup");

    topupBtn.addEventListener("click", () => {
        modal.classList.remove("hidden");
    });

    cancelBtn.addEventListener("click", () => {
        modal.classList.add("hidden");
    });

    confirmBtn.addEventListener("click", async () => {
        const amount = document.getElementById("topupAmount").value;
        if (!amount || isNaN(amount) || amount < 50) {
            alert("Please enter a valid amount (minimum 50 RUB).");
            return;
        }

        try {
            confirmBtn.disabled = true;
            confirmBtn.textContent = "Processing...";
            const url = await currentUser.functions.createPayment(parseFloat(amount), `Topup ${amount} RUB`, window.location.href);
            window.location.href = url; // Redirect to Yookassa
        } catch (err) {
            console.error("Payment creation failed:", err);
            alert("Failed to create payment: " + err.message);
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.textContent = "Proceed";
            modal.classList.add("hidden");
        }
    });
}

async function buySubscription(period, price) {
    const balanceText = document.getElementById("userBalance").textContent;
    const currentBalance = parseFloat(balanceText);

    if (currentBalance < price) {
        alert("Insufficient balance. Please top up first.");
        return;
    }

    if (!confirm(`Are you sure you want to buy the ${period} subscription for ${price} RUB?`)) {
        return;
    }

    try {
        const loading = document.createElement("div");
        loading.id = "purchaseLoading";
        loading.className = "fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50 text-white font-bold text-xl";
        loading.innerText = "Purchasing...";
        document.body.appendChild(loading);

        const result = await currentUser.functions.buySubscription(period);

        if (result.success) {
            alert("Subscription purchased successfully!");
            // Refresh data
            const profile = await currentUser.functions.getProfile();
            updateProfileUI(profile);
            renderMyConfigs(profile.used_configs);
        }
    } catch (err) {
        console.error("Purchase failed:", err);
        alert("Purchase failed: " + err.message);
    } finally {
        const loading = document.getElementById("purchaseLoading");
        if (loading) loading.remove();
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert("Copied to clipboard!");
    }).catch(err => {
        console.error("Failed to copy:", err);
        alert("Failed to copy text.");
    });
}

async function checkPendingPayments() {
    try {
        // We call the function that checks all pending payments for the user
        // This is better than relying on URL params which TMA drops sometimes
        const results = await currentUser.functions.checkPendingPayments();
        if (results && results.length > 0) {
            const confirmed = results.filter(r => r.status === "confirmed");
            if (confirmed.length > 0) {
                alert(`Successfully processed ${confirmed.length} topup(s). Balance updated.`);
                // Refresh profile to show new balance
                const profile = await currentUser.functions.getProfile();
                updateProfileUI(profile);
            }
        }
    } catch (err) {
        console.error("Error checking pending payments:", err);
    }
}
