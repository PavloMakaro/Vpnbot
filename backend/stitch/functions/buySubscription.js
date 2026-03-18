exports = async function(period) {
  const telegramId = context.user.identities[0].id;

  if (!telegramId) {
    throw new Error("No Telegram ID found in context");
  }

  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const plan = SUBSCRIPTION_PERIODS[period];
  if (!plan) {
    throw new Error("Invalid subscription period");
  }

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  // Step 1: Find user and check balance
  const user = await usersCollection.findOne({ _id: telegramId });
  if (!user) {
    throw new Error("User not found");
  }

  const currentBalance = user.balance || 0;
  if (currentBalance < plan.price) {
    throw new Error(`Insufficient funds. Required: ${plan.price}, Balance: ${currentBalance}`);
  }

  // Step 2: Atomically find and reserve an unused configuration
  // Using findOneAndUpdate to prevent race conditions
  const config = await configsCollection.findOneAndUpdate(
    { period: period, used: false },
    { $set: { used: true } },
    { returnNewDocument: true }
  );

  if (!config) {
    throw new Error("No available configurations for this period. Please contact support.");
  }

  // Step 3: Calculate new subscription end date
  let currentEnd = user.subscription_end;
  if (currentEnd) {
    // Attempt to parse existing string date "YYYY-MM-DD HH:MM:SS"
    // For simplicity, we create a new Date. Note: vanilla js date parsing replaces " " with "T"
    let d = new Date(currentEnd.replace(' ', 'T'));
    if (d.getTime() < Date.now()) {
      currentEnd = new Date();
    } else {
      currentEnd = d;
    }
  } else {
    currentEnd = new Date();
  }

  // Add days
  currentEnd.setDate(currentEnd.getDate() + plan.days);

  // Format to standard format like "2023-12-01 12:00:00"
  const pad = (n) => n.toString().padStart(2, '0');
  const newEndDateString = `${currentEnd.getFullYear()}-${pad(currentEnd.getMonth()+1)}-${pad(currentEnd.getDate())} ${pad(currentEnd.getHours())}:${pad(currentEnd.getMinutes())}:${pad(currentEnd.getSeconds())}`;

  // Record used config history
  const usedConfigEntry = {
    config_name: config.name,
    config_link: config.link,
    config_code: config.code,
    period: period,
    issue_date: new Date().toISOString().replace('T', ' ').substring(0, 19),
    user_name: `${user.first_name || ""} (@${user.username || ""})`
  };

  // Step 4: Deduct balance, update subscription end, and append to used_configs
  await usersCollection.updateOne(
    { _id: telegramId },
    {
      $inc: { balance: -plan.price },
      $set: { subscription_end: newEndDateString },
      $push: { used_configs: usedConfigEntry }
    }
  );

  return {
    success: true,
    message: "Subscription purchased successfully",
    config: usedConfigEntry,
    newBalance: currentBalance - plan.price,
    subscriptionEnd: newEndDateString
  };
};
