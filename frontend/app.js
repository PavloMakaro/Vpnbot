const APP_ID = "YOUR_REALM_APP_ID"; // Replace with your Atlas App ID
const app = new Realm.App({ id: APP_ID });

const tg = window.Telegram.WebApp;
tg.expand();

// DOM Elements
const loadingEl = document.getElementById('loading');
const mainContent = document.getElementById('main-content');
const errorState = document.getElementById('error-state');
const errorMessage = document.getElementById('error-message');

const userNameEl = document.getElementById('user-name');
const userHandleEl = document.getElementById('user-handle');
const userAvatarEl = document.getElementById('user-avatar');
const userBalanceEl = document.getElementById('user-balance');
const subStatusEl = document.getElementById('sub-status');
const configsList = document.getElementById('configs-list');
const plansList = document.getElementById('plans-list');

// Top-up modal elements
const topupModal = document.getElementById('topup-modal');
const topupBtn = document.getElementById('topup-btn');
const closeTopupBtn = document.getElementById('close-topup');
const amountBtns = document.querySelectorAll('.amount-btn');
const customAmountInput = document.getElementById('custom-amount');
const confirmTopupBtn = document.getElementById('confirm-topup');

let currentUser = null;
let currentProfile = null;
let selectedAmount = null;

async function initApp() {
  try {
    const initData = tg.initData;

    // Check if we are in test mode or no initData available
    if (!initData) {
      showError("Please open this app from Telegram.");
      return;
    }

    // Authenticate with Realm using Custom Function Auth
    const credentials = Realm.Credentials.function({ initData });
    currentUser = await app.logIn(credentials);

    // After login, fetch profile and configs
    await Promise.all([
      fetchProfile(),
      fetchPlans()
    ]);

    // Ensure we check any pending payments on load without relying on URL params
    await checkPendingPayments();

    showMainContent();
  } catch (error) {
    console.error("Initialization error:", error);
    showError(error.message || "Failed to initialize app.");
  }
}

async function fetchProfile() {
  try {
    currentProfile = await currentUser.functions.getProfile();
    updateProfileUI();
  } catch (err) {
    console.error("Error fetching profile:", err);
    throw err;
  }
}

function updateProfileUI() {
  userNameEl.textContent = currentProfile.first_name || 'User';
  userHandleEl.textContent = currentProfile.username ? `@${currentProfile.username}` : 'No username';
  userAvatarEl.textContent = userNameEl.textContent.charAt(0).toUpperCase();
  userBalanceEl.textContent = currentProfile.balance || 0;

  // Subscription Status
  const subEnd = currentProfile.subscription_end;
  if (subEnd) {
    // Replace ' ' with 'T' for Vanilla JS Safari/iOS compatibility
    const endDate = new Date(subEnd.replace(' ', 'T'));
    if (endDate > new Date()) {
      subStatusEl.innerHTML = `<span class="text-green-600 font-bold">Active</span> until ${endDate.toLocaleDateString()}`;
    } else {
      subStatusEl.innerHTML = `<span class="text-red-500 font-bold">Expired</span> on ${endDate.toLocaleDateString()}`;
    }
  } else {
    subStatusEl.innerHTML = `<span class="text-gray-500 font-bold">No active subscription</span>`;
  }

  // Configs
  const usedConfigs = currentProfile.used_configs || [];
  if (usedConfigs.length > 0) {
    configsList.innerHTML = usedConfigs.map(config => `
      <div class="card p-4 rounded-xl shadow-sm border border-black/5">
        <div class="flex justify-between items-start mb-2">
          <h4 class="font-bold">${config.config_name}</h4>
          <span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full font-medium">${config.period}</span>
        </div>
        <div class="bg-black/5 p-2 rounded-lg flex items-center justify-between">
          <code class="text-xs truncate w-[80%] opacity-80">${config.config_link}</code>
          <button onclick="copyToClipboard('${config.config_link}')" class="text-blue-500 text-sm font-bold active:scale-95 transition-transform p-1">Copy</button>
        </div>
      </div>
    `).join('');
  } else {
    configsList.innerHTML = `<p class="text-sm opacity-70 text-center py-4 italic">No configs issued yet.</p>`;
  }
}

async function fetchPlans() {
  try {
    const plans = await currentUser.functions.getConfigs();

    let html = '';
    for (const [key, plan] of Object.entries(plans)) {
      html += `
        <div class="card p-4 rounded-xl shadow-sm border border-black/5 flex justify-between items-center">
          <div>
            <h4 class="font-bold text-lg">${plan.days} Days</h4>
            <p class="text-sm opacity-70">${plan.price} ₽</p>
          </div>
          <button onclick="buySubscription('${key}')" class="btn-primary px-4 py-2 rounded-lg font-medium shadow-sm active:scale-95 transition-transform">
            Buy Now
          </button>
        </div>
      `;
    }
    plansList.innerHTML = html;
  } catch (err) {
    console.error("Error fetching plans:", err);
  }
}

async function buySubscription(period) {
  try {
    tg.showConfirm(`Are you sure you want to buy a ${period} subscription?`, async (confirmed) => {
      if (!confirmed) return;

      tg.MainButton.showProgress();
      try {
        const result = await currentUser.functions.buySubscription(period);
        if (result.success) {
          tg.showAlert("Subscription purchased successfully!");
          await fetchProfile(); // Refresh UI
        }
      } catch (err) {
        tg.showAlert(err.message || "Failed to purchase subscription.");
      } finally {
        tg.MainButton.hideProgress();
      }
    });
  } catch (err) {
    console.error("Error buying sub:", err);
  }
}

async function checkPendingPayments() {
  try {
    const res = await currentUser.functions.checkPendingPayments();
    if (res.success && res.message.includes("Confirmed")) {
       tg.showAlert("Your pending top-up was confirmed!");
       await fetchProfile();
    }
  } catch(e) {
    console.error("Error checking pending payments:", e);
  }
}

// Top-up Logic
topupBtn.addEventListener('click', () => {
  topupModal.classList.remove('hidden');
  topupModal.classList.add('flex');
});

closeTopupBtn.addEventListener('click', () => {
  topupModal.classList.add('hidden');
  topupModal.classList.remove('flex');
});

amountBtns.forEach(btn => {
  btn.addEventListener('click', (e) => {
    amountBtns.forEach(b => b.classList.remove('bg-blue-100', 'border-blue-500', 'text-blue-700'));
    e.target.classList.add('bg-blue-100', 'border-blue-500', 'text-blue-700');
    selectedAmount = parseInt(e.target.dataset.amount);
    customAmountInput.value = '';
    validateTopup();
  });
});

customAmountInput.addEventListener('input', (e) => {
  amountBtns.forEach(b => b.classList.remove('bg-blue-100', 'border-blue-500', 'text-blue-700'));
  selectedAmount = parseInt(e.target.value);
  validateTopup();
});

function validateTopup() {
  if (selectedAmount && selectedAmount >= 50 && selectedAmount <= 50000) {
    confirmTopupBtn.disabled = false;
  } else {
    confirmTopupBtn.disabled = true;
  }
}

confirmTopupBtn.addEventListener('click', async () => {
  if (!selectedAmount) return;

  tg.MainButton.showProgress();
  try {
    const result = await currentUser.functions.createPayment(selectedAmount);
    if (result.success && result.confirmationUrl) {
      tg.openLink(result.confirmationUrl);
      topupModal.classList.add('hidden');
      topupModal.classList.remove('flex');
    }
  } catch (err) {
    tg.showAlert("Failed to create payment: " + err.message);
  } finally {
    tg.MainButton.hideProgress();
  }
});

// Utils
function showMainContent() {
  loadingEl.classList.add('hidden');
  errorState.classList.add('hidden');
  mainContent.classList.remove('hidden');
}

function showError(msg) {
  loadingEl.classList.add('hidden');
  mainContent.classList.add('hidden');
  errorState.classList.remove('hidden');
  errorState.classList.add('flex');
  errorMessage.textContent = msg;
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    tg.showAlert("Config link copied to clipboard!");
  }).catch(err => {
    console.error('Failed to copy: ', err);
  });
}

// Start app
initApp();
