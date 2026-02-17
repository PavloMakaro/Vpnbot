exports = async function(periodKey) {
  const userId = context.user.id;
  const mongo = context.services.get("mongodb-atlas");
  const usersCollection = mongo.db("vpn_bot").collection("users");
  const configsCollection = mongo.db("vpn_bot").collection("configs");

  const SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
  };

  const plan = SUBSCRIPTION_PERIODS[periodKey];
  if (!plan) {
    throw new Error("Invalid period");
  }

  // Use a session for transaction if cluster supports it, otherwise simulated transaction
  // Atlas Shared Tier (M0) doesn't support transactions easily without specific setup.
  // We'll use sequential updates with optimistic checks for now.

  const user = await usersCollection.findOne({ _id: userId });
  if (user.balance < plan.price) {
    throw new Error("Insufficient funds");
  }

  // Find an available config
  // Note: Data model implies configs are pre-generated and stored in 'configs' collection
  // with a 'period' field (e.g. '1_month') and 'used' boolean.
  const config = await configsCollection.findOneAndUpdate(
    { period: periodKey, used: false },
    { $set: { used: true, used_by: userId, used_at: new Date() } },
    { returnNewDocument: true }
  );

  if (!config) {
    throw new Error("No configs available for this period. Contact support.");
  }

  // Calculate new subscription end date
  let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
  if (currentEnd < new Date()) {
    currentEnd = new Date();
  }
  const newEnd = new Date(currentEnd.getTime() + plan.days * 24 * 60 * 60 * 1000);

  // Update user
  const usedConfigEntry = {
    config_name: config.name,
    config_link: config.link,
    config_code: config.code,
    period: periodKey,
    issue_date: new Date(),
    user_name: user.username
  };

  await usersCollection.updateOne(
    { _id: userId },
    {
      $inc: { balance: -plan.price },
      $set: { subscription_end: newEnd },
      $push: { used_configs: usedConfigEntry }
    }
  );

  return {
    success: true,
    new_balance: user.balance - plan.price,
    subscription_end: newEnd,
    config: usedConfigEntry
  };
};
