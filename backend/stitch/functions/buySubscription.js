exports = async function(period) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("User not authenticated");
  }

  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  if (!SUBSCRIPTION_PERIODS[period]) {
    throw new Error("Invalid subscription period");
  }

  const price = SUBSCRIPTION_PERIODS[period].price;
  const days = SUBSCRIPTION_PERIODS[period].days;

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  // Get user profile
  const userProfile = await usersCollection.findOne({ _id: user.id });
  if (!userProfile) {
    throw new Error("User profile not found");
  }

  // Check balance
  if ((userProfile.balance || 0) < price) {
    throw new Error(`Insufficient funds. You have ${userProfile.balance || 0} ₽, but need ${price} ₽.`);
  }

  // Find and reserve a config atomically
  const reservedConfig = await configsCollection.findOneAndUpdate(
    { period: period, used: false },
    { $set: { used: true, reserved_at: new Date(), reserved_by: user.id } },
    { returnNewDocument: true }
  );

  if (!reservedConfig) {
    throw new Error("No available configs for this period. Please try again later or contact support.");
  }

  // Calculate new subscription end date
  let currentEnd = userProfile.subscription_end ? new Date(userProfile.subscription_end) : new Date();
  if (currentEnd < new Date()) {
    currentEnd = new Date();
  }

  // Add days to current end date
  currentEnd.setDate(currentEnd.getDate() + days);

  const issueDate = new Date().toISOString().replace('T', ' ').substring(0, 19);

  const usedConfigEntry = {
    config_name: reservedConfig.name,
    config_link: reservedConfig.link,
    config_code: reservedConfig.code,
    period: period,
    issue_date: issueDate,
    user_name: `${userProfile.first_name || 'User'} (@${userProfile.username || 'user'})`
  };

  // Deduct balance, update subscription end, and add to used configs
  const updateResult = await usersCollection.updateOne(
    { _id: user.id, balance: { $gte: price } }, // double check balance is still enough
    {
      $inc: { balance: -price },
      $set: { subscription_end: currentEnd },
      $push: { used_configs: usedConfigEntry }
    }
  );

  if (updateResult.modifiedCount !== 1) {
    // If update failed (e.g. balance changed between checks), we need to rollback config reservation
    await configsCollection.updateOne(
      { _id: reservedConfig._id },
      { $set: { used: false }, $unset: { reserved_at: "", reserved_by: "" } }
    );
    throw new Error("Transaction failed. Your balance may have changed. Please try again.");
  }

  return {
    success: true,
    message: "Subscription purchased successfully",
    config: reservedConfig,
    new_balance: userProfile.balance - price,
    subscription_end: currentEnd
  };
};