let tg = window.Telegram.WebApp;
let user = tg.initDataUnsafe.user;
let currentTab = 'home';
let selectedAmount = 0;
let selectedPlan = null;

// Initialize
tg.expand();

async function api(endpoint, method = 'GET', body = null) {
    const headers = {
        'Content-Type': 'application/json',
        'X-Telegram-User-ID': user ? user.id : 'debug' // In production, use initData for verification
    };

    // For debugging in browser without Telegram
    if (!user) {
        console.warn("No Telegram user detected. Using debug ID.");
        // Mock user for testing if needed
        // headers['X-Telegram-User-ID'] = '8320218178';
    }

    try {
        const options = { method, headers };
        if (body) options.body = JSON.stringify(body);

        const response = await fetch('/api' + endpoint, options);
        if (!response.ok) {
             const errorData = await response.json();
             throw new Error(errorData.detail || 'API Error');
        }
        return await response.json();
    } catch (e) {
        tg.showAlert(e.message);
        return null;
    }
}

// Navigation
function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById(tab + '-tab').classList.remove('hidden');

    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`[onclick="switchTab('${tab}')"]`).classList.add('active');

    currentTab = tab;

    if (tab === 'home') loadHome();
    if (tab === 'shop') loadPlans();
    if (tab === 'profile') loadConfigs();
}

// Data Loading
async function loadHome() {
    const data = await api('/me');
    if (!data) return;

    document.getElementById('balance-display').textContent = `${data.balance} ₽`;
    document.getElementById('username-display').textContent = data.first_name;

    const subStatus = document.getElementById('sub-status');
    const subDate = document.getElementById('sub-date');

    if (data.days_left > 0) {
        subStatus.className = 'status-pill status-active';
        subStatus.textContent = 'Active';
        subDate.textContent = `Expires in ${data.days_left} days`;
    } else {
        subStatus.className = 'status-pill status-inactive';
        subStatus.textContent = 'Inactive';
        subDate.textContent = 'No active subscription';
    }
}

async function loadPlans() {
    const plans = await api('/plans');
    if (!plans) return;

    const container = document.getElementById('plans-container');
    container.innerHTML = '';

    for (const [key, plan] of Object.entries(plans)) {
        const el = document.createElement('div');
        el.className = 'card plan-card';
        el.onclick = () => selectPlan(el, key, plan);
        el.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h3>${plan.days} Days</h3>
                    <div class="text-secondary">${plan.desc || 'High speed VPN'}</div>
                </div>
                <div class="plan-price">${plan.price} ₽</div>
            </div>
        `;
        container.appendChild(el);
    }
}

function selectPlan(el, key, plan) {
    document.querySelectorAll('.plan-card').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    selectedPlan = { key, ...plan };
    document.getElementById('buy-btn').textContent = `Buy for ${plan.price} ₽`;
    document.getElementById('buy-btn').disabled = false;
}

async function buySubscription() {
    if (!selectedPlan) return;

    tg.MainButton.showProgress();
    const result = await api('/buy', 'POST', { period: selectedPlan.key });
    tg.MainButton.hideProgress();

    if (result && result.success) {
        tg.showAlert('Subscription purchased successfully!');
        switchTab('home');
    }
}

async function loadConfigs() {
    const configs = await api('/configs');
    if (!configs) return;

    const container = document.getElementById('configs-list');
    container.innerHTML = '';

    if (configs.length === 0) {
        container.innerHTML = '<div style="text-align:center; color:#86868b; padding:20px;">No configs found</div>';
        return;
    }

    configs.forEach(conf => {
        const el = document.createElement('div');
        el.className = 'config-item';
        el.innerHTML = `
            <div class="config-info">
                <div class="config-name">${conf.config_name}</div>
                <div class="config-date">Expires: ${conf.period}</div>
            </div>
            <button class="btn btn-small btn-secondary" onclick="copyConfig('${conf.config_link}')">Copy</button>
        `;
        container.appendChild(el);
    });
}

function copyConfig(link) {
    navigator.clipboard.writeText(link).then(() => {
        tg.showAlert('Config link copied to clipboard!');
    });
}

// Topup Logic
function selectAmount(amount) {
    selectedAmount = amount;
    document.getElementById('amount-input').value = amount;
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
    // Visual update logic if needed
}

async function initiateTopup() {
    const inputVal = document.getElementById('amount-input').value;
    const amount = parseInt(inputVal);

    if (!amount || amount < 50) {
        tg.showAlert('Minimum amount is 50 ₽');
        return;
    }

    tg.MainButton.showProgress();
    const result = await api('/topup', 'POST', { amount });
    tg.MainButton.hideProgress();

    if (result && result.confirmation_url) {
        tg.openLink(result.confirmation_url);
    }
}

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    loadHome();

    // Chips listener
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', function() {
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
            document.getElementById('amount-input').value = this.dataset.amount;
        });
    });
});
