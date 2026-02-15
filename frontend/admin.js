const tg = window.Telegram.WebApp;
tg.expand();

const APP_ID = "vpn_bot-xxxxx"; // Replace with your App ID
const app = new Realm.App({ id: APP_ID });
let user = null;

async function init() {
    try {
        const credentials = Realm.Credentials.function({ initData: tg.initData });
        user = await app.logIn(credentials);
        loadStats();
    } catch (err) {
        alert("Auth failed: " + err.message);
    }
}

async function addConfigs() {
    const period = document.getElementById('period-select').value;
    const text = document.getElementById('configs-input').value;
    const resultEl = document.getElementById('add-result');

    if (!text.trim()) return;

    resultEl.textContent = "Processing...";

    try {
        const res = await user.functions.addConfigs(period, text);
        resultEl.textContent = `Success: Added ${res.added} configs.`;
        document.getElementById('configs-input').value = '';
        loadStats();
    } catch (err) {
        resultEl.textContent = "Error: " + err.message;
        resultEl.classList.add('text-red-500');
    }
}

async function loadStats() {
    try {
        const stats = await user.functions.getStats();
        document.getElementById('stat-users').textContent = stats.total_users;
        document.getElementById('stat-revenue').textContent = `${stats.total_revenue} ₽`;
        document.getElementById('stat-active').textContent = stats.active_subscriptions;
        document.getElementById('stat-configs').textContent = stats.configs_available;
    } catch (err) {
        console.error(err);
    }
}

init();
