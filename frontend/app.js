const REALM_APP_ID = "vpn-bot-xyz"; // REPLACE WITH YOUR REALM APP ID
const app = new Realm.App({ id: REALM_APP_ID });
const tg = window.Telegram.WebApp;

// Expand to full height
tg.expand();

let currentUser = null;

async function initApp() {
  try {
    // Authenticate
    if (!app.currentUser) {
      // Use Custom Function Auth with Telegram initData
      const credentials = Realm.Credentials.function({
        initData: tg.initData
      });
      currentUser = await app.logIn(credentials);
    } else {
      currentUser = app.currentUser;
    }

    // Load initial data
    await refreshProfile();
    await loadConfigs();

    // Show UI
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('content').classList.remove('hidden');
    document.getElementById('nav').classList.remove('hidden');
    document.getElementById('nav').classList.add('flex'); // Because I used flex hidden initially

    // Setup User Info
    const user = tg.initDataUnsafe.user;
    if (user) {
      document.getElementById('user-name').innerText = user.first_name;
      document.getElementById('user-initials').innerText = user.first_name.charAt(0).toUpperCase();
    }

  } catch (err) {
    console.error("Init Error:", err);
    showError(err.message || "Failed to initialize app");
  }
}

async function refreshProfile() {
  try {
    const profile = await currentUser.functions.getUserProfile();
    if (profile.error) throw new Error(profile.error);

    document.getElementById('user-balance').innerText = `${profile.balance} ₽`;

    // Subscription Status
    const statusEl = document.getElementById('sub-status');
    const detailsEl = document.getElementById('sub-details');
    const indicator = document.getElementById('sub-indicator');

    if (profile.days_left > 0) {
      statusEl.innerText = "Active";
      statusEl.classList.remove('text-red-500');
      statusEl.classList.add('text-green-500');

      const endDate = new Date(profile.subscription_end).toLocaleDateString();
      detailsEl.innerText = `${profile.days_left} days left (expires ${endDate})`;

      indicator.classList.remove('bg-gray-600');
      indicator.classList.add('bg-green-500');
    } else {
      statusEl.innerText = "Inactive";
      statusEl.classList.add('text-gray-400');

      detailsEl.innerText = "No active subscription";

      indicator.classList.remove('bg-green-500');
      indicator.classList.add('bg-gray-600');
    }
  } catch (err) {
    console.error("Profile Error:", err);
  }
}

async function loadConfigs() {
  try {
    const configs = await currentUser.functions.getConfigs();
    const list = document.getElementById('configs-list');
    list.innerHTML = "";

    if (configs && configs.length > 0) {
      configs.forEach(config => {
        const item = document.createElement('div');
        item.className = "bg-gray-800 p-4 rounded-xl border border-gray-700 mb-3";
        item.innerHTML = `
          <div class="flex justify-between items-center mb-2">
            <span class="font-bold text-blue-400">${config.config_name}</span>
            <span class="text-xs text-gray-500">${new Date(config.issue_date).toLocaleDateString()}</span>
          </div>
          <div class="bg-gray-900 p-2 rounded text-xs break-all font-mono text-gray-400 select-all cursor-pointer" onclick="copyToClipboard('${config.config_link}')">
            ${config.config_link.substring(0, 40)}...
          </div>
          <button onclick="copyToClipboard('${config.config_link}')" class="mt-2 text-xs text-blue-500 w-full text-center py-1 hover:bg-gray-700 rounded transition">Copy Link</button>
        `;
        list.appendChild(item);
      });
    } else {
      list.innerHTML = `<div class="p-6 text-center text-gray-500 bg-gray-800/50 rounded-xl border border-gray-800 border-dashed">
              <p>No configs found.</p>
              <button onclick="showView('shop')" class="mt-2 text-blue-400 text-sm hover:underline">Buy a subscription</button>
            </div>`;
    }
  } catch (err) {
    console.error("Configs Error:", err);
  }
}

async function buySubscription(period, price) {
  // Confirm
  tg.showConfirm(`Buy ${period.replace('_', ' ')} subscription for ${price} ₽?`, async (confirmed) => {
    if (confirmed) {
      showLoading(true);
      try {
        const result = await currentUser.functions.buySubscription(period);
        if (result.success) {
          tg.showAlert("Success! Config added to My Configs.");
          await refreshProfile();
          await loadConfigs();
          showView('configs');
        }
      } catch (err) {
        tg.showAlert(`Error: ${err.message}`);
      } finally {
        showLoading(false);
      }
    }
  });
}

async function initTopup(amount) {
  if (!amount || amount < 50) {
    tg.showAlert("Minimum amount is 50 ₽");
    return;
  }

  showLoading(true);
  try {
    const result = await currentUser.functions.createPayment(parseFloat(amount), `Topup ${amount} RUB`);
    if (result.confirmation_url) {
      tg.openLink(result.confirmation_url);
      // Ideally show a pending status or instruction
      tg.showAlert("Payment link opened. After payment, return here and refresh.");
    }
  } catch (err) {
    tg.showAlert(`Error: ${err.message}`);
  } finally {
    showLoading(false);
  }
}

function showView(viewName) {
  // Hide all views
  document.querySelectorAll('.view').forEach(el => el.classList.add('hidden'));

  // Show selected
  const view = document.getElementById(`view-${viewName}`);
  if (view) view.classList.remove('hidden');

  // Update Nav (if applicable)
  // Simple logic to highlight active nav
  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('text-blue-500'));
  const navBtn = document.getElementById(`nav-${viewName}`);
  if (navBtn) navBtn.classList.add('text-blue-500');
}

function showError(msg) {
  document.getElementById('loading').classList.add('hidden');
  document.getElementById('error').classList.remove('hidden');
  document.getElementById('error-message').innerText = msg;
}

function showLoading(show) {
  if (show) {
    tg.MainButton.showProgress();
  } else {
    tg.MainButton.hideProgress();
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    tg.showAlert("Copied to clipboard!");
  }).catch(err => {
    console.error('Async: Could not copy text: ', err);
  });
}

// Initial View
showView('shop');

// Start
initApp();
