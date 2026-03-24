const APP_ID = "YOUR_ATLAS_APP_ID"; // Replace with real ID
const app = new Realm.App({ id: APP_ID });

document.addEventListener("DOMContentLoaded", async () => {
    try {
        if (!window.Telegram.WebApp.initData) {
            console.warn("Running outside of Telegram WebApp environment.");
        }

        window.Telegram.WebApp.expand();

        // 1. Authenticate with Custom JWT/Function
        const initData = window.Telegram.WebApp.initData || "mockInitData"; // Fallback for testing if necessary
        const credentials = Realm.Credentials.custom({ initData });

        await app.logIn(credentials);
        console.log("Logged in successfully!", app.currentUser.id);

        // Load UI components...
        await loadUserData();

        // Verify pending payments upon load
        await verifyPendingPayments();

        // Fetch subscriptions prices
        await loadSubscriptions();

        // Toggle UI
        document.getElementById("loader").style.display = "none";
        document.getElementById("app").style.display = "block";

    } catch (error) {
        console.error("Failed to initialize app:", error);
        document.getElementById("loader").innerHTML = `<p class="text-red-500 font-bold p-4 text-center">Authentication Failed: ${error.message}</p>`;
    }
});

// Load User Data
async function loadUserData() {
    try {
        const user = app.currentUser;
        const profile = await user.functions.getProfile();

        // Render Profile
        document.getElementById("userName").textContent = `${profile.first_name} (@${profile.username})`;
        document.getElementById("userBalance").textContent = profile.balance;

        // Subscription Status
        const statusEl = document.getElementById("subStatus");
        if (profile.subscription_end) {
            // Memory directive: parse dates with 'T' for iOS compatibility
            const endDateString = profile.subscription_end.replace(' ', 'T');
            const end = new Date(endDateString);

            if (end > new Date()) {
                const daysLeft = Math.ceil((end - new Date()) / (1000 * 60 * 60 * 24));
                statusEl.innerHTML = `<span class="text-green-500">Active</span> - ${daysLeft} days left (expires ${end.toLocaleDateString()})`;
            } else {
                statusEl.innerHTML = `<span class="text-red-500">Expired</span> - ${end.toLocaleDateString()}`;
            }
        } else {
            statusEl.innerHTML = `<span class="text-gray-500">No active subscription</span>`;
        }

        // Render Configs
        const configsContainer = document.getElementById("myConfigs");
        if (profile.used_configs && profile.used_configs.length > 0) {
            configsContainer.innerHTML = ''; // Clear default
            profile.used_configs.forEach(conf => {
                const dateStr = conf.issue_date.replace(' ', 'T');
                const issueDate = new Date(dateStr).toLocaleDateString();

                const div = document.createElement("div");
                div.className = "bg-gray-50 p-3 rounded border border-gray-200";
                div.innerHTML = `
                    <p class="font-bold text-gray-800">${conf.config_name} (${conf.period})</p>
                    <p class="text-xs text-gray-500 mb-2">Issued: ${issueDate}</p>
                    <code class="block bg-gray-100 p-2 text-xs rounded break-all border overflow-x-auto">${conf.config_link}</code>
                `;
                configsContainer.appendChild(div);
            });
        }

    } catch (e) {
        console.error("Failed fetching user profile", e);
    }
}

// Check Pending Payments
async function verifyPendingPayments() {
    try {
        const user = app.currentUser;
        const result = await user.functions.checkPendingPayments();

        if (result.success && result.processed > 0) {
            alert(`Processed ${result.processed} pending payments:\n${result.messages.join('\n')}`);
        }
    } catch (e) {
        console.error("Failed checking pending payments:", e);
    }
}

// Load Subscription Prices
async function loadSubscriptions() {
    try {
        const user = app.currentUser;
        const periods = await user.functions.getConfigs();

        const container = document.getElementById("subOptions");
        container.innerHTML = '';

        for (const [key, details] of Object.entries(periods)) {
            const btn = document.createElement('button');
            btn.className = "w-full bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold py-2 px-4 border border-blue-300 rounded shadow-sm transition flex justify-between";
            btn.innerHTML = `<span>${details.days} Days</span> <span>${details.price} RUB</span>`;

            btn.onclick = () => purchaseSubscription(key, details.price);

            container.appendChild(btn);
        }

    } catch (e) {
        console.error("Failed loading sub prices:", e);
        document.getElementById("subOptions").innerHTML = `<p class="text-red-500 text-sm">Error loading subscriptions.</p>`;
    }
}

// Purchase Subscription
async function purchaseSubscription(periodKey, price) {
    const btn = event.currentTarget;
    const ogHtml = btn.innerHTML;
    btn.innerHTML = 'Processing...';
    btn.disabled = true;

    const msgEl = document.getElementById("subMsg");
    msgEl.className = "text-xs mt-3 text-center";
    msgEl.textContent = "";

    try {
        const user = app.currentUser;
        const response = await user.functions.buySubscription(periodKey);

        if (response.success) {
            msgEl.textContent = "Subscription purchased successfully!";
            msgEl.classList.add("text-green-500");
            // Reload user data to show new balance and configs
            await loadUserData();
        } else {
            msgEl.textContent = response.message + (response.needTopUp ? ` (Need ${response.needTopUp} RUB more)` : "");
            msgEl.classList.add("text-red-500");
        }
    } catch (e) {
        console.error("Purchase error", e);
        msgEl.textContent = "An error occurred during purchase.";
        msgEl.classList.add("text-red-500");
    } finally {
        btn.innerHTML = ogHtml;
        btn.disabled = false;
    }
}

// Top-up Event Listener
document.getElementById("btnTopup").addEventListener("click", async () => {
    const amountInput = document.getElementById("topupAmount");
    const amount = parseInt(amountInput.value);
    const msgEl = document.getElementById("topupMsg");

    msgEl.classList.remove("hidden");

    if (!amount || amount < 50 || amount > 50000) {
        msgEl.textContent = "Enter an amount between 50 and 50000 RUB.";
        return;
    }

    const btn = document.getElementById("btnTopup");
    const ogText = btn.textContent;
    btn.textContent = "Wait...";
    btn.disabled = true;

    try {
        const user = app.currentUser;

        // Pass current URL for redirect return
        const returnUrl = window.location.href;

        const response = await user.functions.createPayment(amount, returnUrl);

        if (response.confirmationUrl) {
             window.location.href = response.confirmationUrl;
        } else {
             msgEl.textContent = "Failed to create payment link.";
        }
    } catch (e) {
        console.error("Topup error", e);
        msgEl.textContent = "Error initiating top-up.";
    } finally {
        btn.textContent = ogText;
        btn.disabled = false;
    }
});