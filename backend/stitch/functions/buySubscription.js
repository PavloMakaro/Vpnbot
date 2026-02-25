exports = async function(period) {
  // Buy a subscription for the given period

  const user = context.user;
  if (!user || !user.id) throw new Error("User not authenticated");

  const periods = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
  };

  if (!periods[period]) throw new Error("Invalid period");

  const price = periods[period].price;
  const daysToAdd = periods[period].days;

  const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const configs = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  // 1. Deduct balance
  const userUpdate = await users.findOneAndUpdate(
    { _id: user.id, balance: { $gte: price } },
    { $inc: { balance: -price } },
    { returnNewDocument: true }
  );

  if (!userUpdate) {
    throw new Error("Insufficient balance");
  }

  // 2. Reserve config
  const config = await configs.findOneAndUpdate(
    { period: period, used: false },
    { $set: { used: true } },
    { returnNewDocument: true }
  );

  if (!config) {
    // Refund balance
    await users.updateOne(
      { _id: user.id },
      { $inc: { balance: price } }
    );
    throw new Error("No configs available for this period");
  }

  // 3. Update user subscription and add config
  // Calculate new subscription end date
  let currentEnd = userUpdate.subscription_end ? new Date(userUpdate.subscription_end) : new Date();
  if (currentEnd < new Date()) {
    currentEnd = new Date();
  }
  const newEnd = new Date(currentEnd.getTime() + daysToAdd * 24 * 60 * 60 * 1000);

  const usedConfig = {
    config_name: config.name,
    config_link: config.link,
    config_code: config.code,
    period: period,
    issue_date: new Date(),
    user_name: `${userUpdate.first_name} (@${userUpdate.username})`
  };

  await users.updateOne(
    { _id: user.id },
    {
      $set: { subscription_end: newEnd },
      $push: { used_configs: usedConfig }
    }
  );

  return {
    success: true,
    message: "Subscription purchased successfully",
    config: usedConfig,
    new_balance: userUpdate.balance,
  };
};
