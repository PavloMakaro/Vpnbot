exports = async function(period) {
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");
  const userId = context.user.id;

  const SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
  };

  if (!SUBSCRIPTION_PERIODS[period]) {
      throw new Error("Invalid period");
  }

  const price = SUBSCRIPTION_PERIODS[period].price;
  const days = SUBSCRIPTION_PERIODS[period].days;

  // 1. Check user balance initially
  const user = await usersCollection.findOne({ _id: userId });
  if (!user) throw new Error("User not found");
  if (user.balance < price) {
      throw new Error("Insufficient balance");
  }

  // 2. Reserve config
  // Use findOneAndUpdate to atomically find and mark as used
  // Note: Adjust specific syntax based on your Realm/Atlas Function version if needed.
  // Standard: returns object with 'value' property containing the document?
  // Or returns document directly?
  // We will assume it returns the document.

  const config = await configsCollection.findOneAndUpdate(
      { used: false, period: period }, // Query
      { $set: { used: true, used_by: userId, used_at: new Date() } }, // Update
      { returnNewDocument: true } // Options
  );

  if (!config) {
      throw new Error("No available configs for this period");
  }

  // 3. Update user (deduct balance, add config, update sub end)
  let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
  if (currentEnd < new Date()) {
      currentEnd = new Date();
  }
  currentEnd.setDate(currentEnd.getDate() + days);

  const usedConfig = {
      config_name: config.name,
      config_link: config.link,
      config_code: config.code,
      period: period,
      issue_date: new Date(),
      user_name: user.username
  };

  // Atomic update with balance check to prevent race conditions
  const result = await usersCollection.updateOne(
      { _id: userId, balance: { $gte: price } },
      {
          $inc: { balance: -price },
          $push: { used_configs: usedConfig },
          $set: { subscription_end: currentEnd }
      }
  );

  if (result.modifiedCount === 0) {
      // Balance insufficient (changed meanwhile) or user deleted
      // Release config
      await configsCollection.updateOne(
          { _id: config._id },
          { $set: { used: false }, $unset: { used_by: "", used_at: "" } }
      );
      throw new Error("Insufficient balance or error updating user");
  }

  return {
      success: true,
      config: usedConfig,
      new_balance: user.balance - price,
      subscription_end: currentEnd
  };
};
