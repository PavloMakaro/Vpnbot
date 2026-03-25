exports = async function(periodKey) {
  const telegramId = context.user.identities[0].id;
  if (!telegramId) throw new Error("Not authenticated");

  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const periodData = SUBSCRIPTION_PERIODS[periodKey];
  if (!periodData) throw new Error("Invalid period");

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  // Step 1: Check user balance
  const user = await usersCollection.findOne({ telegram_id: telegramId });
  if (!user) throw new Error("User not found");

  const balance = user.balance || 0;
  if (balance < periodData.price) throw new Error(`Insufficient balance. You have ${balance} RUB, but need ${periodData.price} RUB.`);

  // Step 2: Reserve an available config for the chosen period
  const reservedConfig = await configsCollection.findOneAndUpdate(
    { period: periodKey, used: false },
    { $set: { used: true, reserved_at: new Date() } },
    { returnNewDocument: true }
  );

  if (!reservedConfig) throw new Error("No available configs for this period. Please try again later or contact support.");

  // Step 3: Deduct balance and add subscription & config
  const issueDate = new Date();
  let subscriptionEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();

  // If subscription expired, restart from today
  if (subscriptionEnd < issueDate) {
    subscriptionEnd = new Date();
  }

  // Add days
  subscriptionEnd.setDate(subscriptionEnd.getDate() + periodData.days);

  const usedConfig = {
    config_name: reservedConfig.name,
    config_link: reservedConfig.link,
    config_code: reservedConfig.code,
    period: periodKey,
    issue_date: issueDate.toISOString().replace(/T/, ' ').replace(/\..+/, ''),
    user_name: `${user.first_name} (@${user.username})`
  };

  await usersCollection.updateOne(
    { telegram_id: telegramId },
    {
      $inc: { balance: -periodData.price },
      $set: { subscription_end: subscriptionEnd.toISOString().replace(/T/, ' ').replace(/\..+/, '') },
      $push: { used_configs: usedConfig }
    }
  );

  return { success: true, config: reservedConfig, new_balance: balance - periodData.price };
};
