exports = async function(period) {
  const tgId = context.user.identities[0].id;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  const subscriptionPeriods = {
    "1_month": { price: 50, days: 30 },
    "2_months": { price: 90, days: 60 },
    "3_months": { price: 120, days: 90 }
  };

  if (!subscriptionPeriods[period]) {
    throw new Error("Invalid subscription period.");
  }

  const { price, days } = subscriptionPeriods[period];

  const user = await usersCollection.findOne({ _id: tgId });
  if (!user) {
    throw new Error("User not found.");
  }

  if (user.balance < price) {
    throw new Error("Insufficient balance.");
  }

  // Atomically find and reserve a config
  const reservedConfig = await configsCollection.findOneAndUpdate(
    { period: period, used: false },
    { $set: { used: true } },
    { returnNewDocument: true }
  );

  if (!reservedConfig) {
    throw new Error("No available configs for this period.");
  }

  // Calculate new subscription end date
  let newSubscriptionEnd;
  const now = new Date();
  if (user.subscription_end && new Date(user.subscription_end) > now) {
    newSubscriptionEnd = new Date(new Date(user.subscription_end).getTime() + days * 24 * 60 * 60 * 1000);
  } else {
    newSubscriptionEnd = new Date(now.getTime() + days * 24 * 60 * 60 * 1000);
  }

  // Update user profile
  const updatedUser = await usersCollection.findOneAndUpdate(
    { _id: tgId, balance: { $gte: price } }, // double check balance
    {
      $inc: { balance: -price },
      $set: { subscription_end: newSubscriptionEnd.toISOString() },
      $push: {
        used_configs: {
          config_name: reservedConfig.name,
          config_link: reservedConfig.link,
          config_code: reservedConfig.code,
          period: period,
          issue_date: new Date().toISOString(),
          user_name: `${user.first_name} (@${user.username})`
        }
      }
    },
    { returnNewDocument: true }
  );

  if (!updatedUser) {
    // Revert config if balance update fails
    await configsCollection.updateOne({ _id: reservedConfig._id }, { $set: { used: false } });
    throw new Error("Transaction failed due to concurrent modification.");
  }

  return { success: true, config: reservedConfig, newBalance: updatedUser.balance };
};