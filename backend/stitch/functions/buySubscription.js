exports = async function(periodKey) {
  const currentUser = context.user;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  // Define prices and periods (should match getConfigs)
  const SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
  };

  if (!SUBSCRIPTION_PERIODS[periodKey]) {
    throw new Error("Invalid subscription period");
  }

  const plan = SUBSCRIPTION_PERIODS[periodKey];
  const user = await usersCollection.findOne({ _id: currentUser.id });

  if (!user) throw new Error("User not found");

  if (user.balance < plan.price) {
    throw new Error("Insufficient balance");
  }

  // Find an available config
  // We atomically find and update to avoid race conditions
  const config = await configsCollection.findOneAndUpdate(
    { period: periodKey, used: false },
    { $set: { used: true, assigned_to: currentUser.id, assigned_at: new Date() } },
    { returnNewDocument: true }
  );

  if (!config) {
    throw new Error("No available configs for this period. Please contact support.");
  }

  // Update user balance and subscription
  let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
  if (currentEnd < new Date()) currentEnd = new Date();

  currentEnd.setDate(currentEnd.getDate() + plan.days);

  const usedConfigEntry = {
    config_name: config.name,
    config_link: config.link,
    config_code: config.code,
    period: periodKey,
    issue_date: new Date(),
    user_name: user.username
  };

  await usersCollection.updateOne(
    { _id: currentUser.id },
    {
      $inc: { balance: -plan.price },
      $set: { subscription_end: currentEnd },
      $push: { used_configs: usedConfigEntry }
    }
  );

  return {
    success: true,
    new_balance: user.balance - plan.price,
    subscription_end: currentEnd,
    config: usedConfigEntry
  };
};