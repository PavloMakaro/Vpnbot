exports = async function(periodKey) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("Authentication required.");
  }

  const telegramId = user.id;
  const mongodb = context.services.get("mongodb-atlas");
  const db = mongodb.db("vpn_bot");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const periodData = SUBSCRIPTION_PERIODS[periodKey];
  if (!periodData) {
    throw new Error("Invalid subscription period.");
  }

  // 1. Fetch user to check balance
  const userProfile = await usersCollection.findOne({ _id: telegramId });
  if (!userProfile) {
    throw new Error("User profile not found.");
  }

  const userBalance = userProfile.balance || 0;
  if (userBalance < periodData.price) {
    throw new Error(`Insufficient funds. Required: ${periodData.price} ₽, Available: ${userBalance} ₽`);
  }

  // 2. Atomically reserve a config
  const reservedConfig = await configsCollection.findOneAndUpdate(
    { period: periodKey, used: false },
    { $set: { used: true } },
    { returnNewDocument: true }
  );

  if (!reservedConfig) {
    throw new Error(`No available configs for period: ${periodKey}.`);
  }

  // 3. Calculate new subscription end date
  let currentEnd = userProfile.subscription_end ? new Date(userProfile.subscription_end) : new Date();
  if (currentEnd < new Date()) {
    currentEnd = new Date(); // If expired, start from now
  }

  const addDays = periodData.days;
  const newEnd = new Date(currentEnd.getTime() + (addDays * 24 * 60 * 60 * 1000));

  // 4. Update user profile (deduct balance, extend subscription, add used config)
  const username = userProfile.username || 'user';
  const firstName = userProfile.first_name || 'User';

  const usedConfigEntry = {
    config_name: reservedConfig.name,
    config_link: reservedConfig.link,
    config_code: reservedConfig.code,
    period: periodKey,
    issue_date: new Date().toISOString(), // Keeping format similar to python
    user_name: `${firstName} (@${username})`
  };

  const updatedUser = await usersCollection.findOneAndUpdate(
    { _id: telegramId },
    {
      $inc: { balance: -periodData.price },
      $set: { subscription_end: newEnd },
      $push: { used_configs: usedConfigEntry }
    },
    { returnNewDocument: true }
  );

  if (!updatedUser) {
    // Attempted to update but failed (this shouldn't happen unless user was deleted)
    throw new Error("Failed to update user profile. Please contact support.");
  }

  return {
    success: true,
    message: `Subscription purchased successfully!`,
    amount_deducted: periodData.price,
    new_balance: updatedUser.balance,
    subscription_end: newEnd,
    config: {
      name: reservedConfig.name,
      link: reservedConfig.link,
      code: reservedConfig.code,
      days: periodData.days
    }
  };
};
