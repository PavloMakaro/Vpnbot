const app = new window.Realm.App({ id: "YOUR_APP_ID" });

document.addEventListener("DOMContentLoaded", async () => {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    const initData = tg.initData || "dev_mock_data";

    try {
        const credentials = window.Realm.Credentials.function({ initData });
        const user = await app.logIn(credentials);

        await loadDashboard();

    } catch (error) {
        console.error("Login failed:", error);
        document.getElementById("loading").innerHTML = `<p class="text-red-500">Authentication failed.</p>`;
    }
});

async function loadDashboard() {
    try {
        const profile = await app.currentUser.functions.getProfile();
        const configs = await app.currentUser.functions.getConfigs();

        document.getElementById("loading").classList.add("hidden");
        document.getElementById("main-content").classList.remove("hidden");

        document.getElementById("balance-display").innerText = `${profile.balance} RUB`;

        const subStatus = document.getElementById("sub-status");
        if (profile.subscription_end) {
            const endDate = new Date(profile.subscription_end);
            if (endDate > new Date()) {
                subStatus.innerText = `Active until ${endDate.toLocaleDateString()}`;
                subStatus.classList.replace("text-green-900", "text-blue-900");
                subStatus.parentElement.classList.replace("bg-green-100", "bg-blue-100");
            } else {
                subStatus.innerText = "Expired";
                subStatus.classList.replace("text-green-900", "text-red-900");
                subStatus.parentElement.classList.replace("bg-green-100", "bg-red-100");
            }
        }

        const plansContainer = document.getElementById("plans-container");
        plansContainer.innerHTML = '';
        for (const [key, plan] of Object.entries(configs)) {
            const btn = document.createElement("button");
            btn.className = `w-full text-left p-4 rounded shadow transition ${plan.available ? 'bg-white hover:bg-gray-50 text-gray-800' : 'bg-gray-100 text-gray-400 cursor-not-allowed'}`;
            btn.innerHTML = `
                <div class="flex justify-between items-center">
                    <span class="font-bold">${plan.title}</span>
                    <span class="font-bold text-blue-600">${plan.price} RUB</span>
                </div>
            `;
            if (plan.available) {
                btn.onclick = () => buySubscription(key, plan.price, profile.balance);
            }
            plansContainer.appendChild(btn);
        }

        const configsContainer = document.getElementById("configs-container");
        configsContainer.innerHTML = '';
        if (profile.used_configs && profile.used_configs.length > 0) {
            profile.used_configs.forEach(conf => {
                const div = document.createElement("div");
                div.className = "bg-gray-50 p-4 rounded shadow text-gray-800 break-all";
                // Replacing spaces with 'T' in case dateStr contains spaces to ensure ISO 8601 compliance
                const dateStr = typeof conf.issue_date === 'string' ? conf.issue_date.replace(' ', 'T') : conf.issue_date;
                const issueDate = new Date(dateStr).toLocaleDateString();
                div.innerHTML = `
                    <p class="font-bold text-sm mb-1">${conf.config_name}</p>
                    <p class="text-xs text-gray-500 mb-2">Issued: ${issueDate}</p>
                    <code class="text-xs block bg-gray-200 p-2 rounded select-all">${conf.config_link}</code>
                `;
                configsContainer.appendChild(div);
            });
        } else {
            configsContainer.innerHTML = '<p class="text-sm text-gray-500">No configs issued yet.</p>';
        }

    } catch (error) {
        console.error("Failed to load dashboard:", error);
        alert("Failed to load dashboard.");
    }
}

async function buySubscription(periodKey, price, balance) {
    if (balance < price) {
        alert("Insufficient balance. Please top up.");
        return;
    }

    if (!confirm(`Buy subscription for ${price} RUB?`)) {
        return;
    }

    try {
        const result = await app.currentUser.functions.buySubscription(periodKey);
        if (result.success) {
            alert("Subscription purchased successfully!");
            await loadDashboard();
        }
    } catch (error) {
        console.error("Purchase failed:", error);
        alert(`Failed to purchase subscription: ${error.message}`);
    }
}

document.getElementById("btn-topup").onclick = () => {
    document.getElementById("topup-modal").classList.remove("hidden");
};

document.getElementById("btn-cancel-topup").onclick = () => {
    document.getElementById("topup-modal").classList.add("hidden");
};

document.getElementById("btn-confirm-topup").onclick = async () => {
    const amountStr = document.getElementById("topup-amount").value;
    const amount = parseInt(amountStr);

    if (isNaN(amount) || amount < 50) {
        alert("Minimum amount is 50 RUB.");
        return;
    }

    try {
        document.getElementById("btn-confirm-topup").innerText = "Processing...";
        const payment = await app.currentUser.functions.createPayment(amount, window.location.href);
        if (payment && payment.confirmation && payment.confirmation.confirmation_url) {
            window.location.href = payment.confirmation.confirmation_url;
        } else {
            alert("Failed to create payment URL.");
        }
    } catch (error) {
        console.error("Topup failed:", error);
        alert(`Failed to create payment: ${error.message}`);
    } finally {
        document.getElementById("btn-confirm-topup").innerText = "Continue";
        document.getElementById("topup-modal").classList.add("hidden");
    }
};

window.addEventListener("focus", async () => {
    if (app && app.currentUser) {
        try {
            const pending = await app.currentUser.functions.checkPendingPayments();
            if (pending && pending.length > 0) {
                const confirmed = pending.filter(p => p.status === "confirmed").length;
                if (confirmed > 0) {
                    alert(`${confirmed} payment(s) confirmed!`);
                    await loadDashboard();
                }
            }
        } catch (error) {
            console.error("Failed to check pending payments:", error);
        }
    }
});