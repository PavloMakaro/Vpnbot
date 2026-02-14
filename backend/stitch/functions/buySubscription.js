exports = async function(period) {
  const users = context.services.get("mongodb-atlas").db("vpn_bot_db").collection("users");
  const configs = context.services.get("mongodb-atlas").db("vpn_bot_db").collection("configs");

  const userId = context.user.id;
  const periodDetails = {
    '1_month': { days: 30, price: 50 },
    '2_months': { days: 60, price: 90 },
    '3_months': { days: 90, price: 120 }
  };

  if (!periodDetails[period]) {
    throw new Error("Invalid period");
  }

  const { days, price } = periodDetails[period];

  // 1. Get User
  const user = await users.findOne({_id: userId});
  if (!user || user.balance < price) {
    throw new Error("Insufficient balance");
  }

  // 2. Find Config
  const config = await configs.findOne({
    period: period,
    used: false
  });

  if (!config) {
    throw new Error("No configs available for this period. Contact support.");
  }

  // 3. Deduct Balance and Update Config (Ideally use transaction)
  // Since transactional support depends on cluster tier, we'll do sequential updates.

  // Mark config as used
  await configs.updateOne(
    { _id: config._id },
    { $set: { used: true, user_id: userId, used_at: new Date() } }
  );

  // Update User Balance & Subscription
  let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
  if (currentEnd < new Date()) currentEnd = new Date();

  const newEnd = new Date(currentEnd.getTime() + days * 24 * 60 * 60 * 1000);

  await users.updateOne(
    { _id: userId },
    {
      $inc: { balance: -price },
      $set: { subscription_end: newEnd },
      $push: {
        used_configs: {
          config_id: config._id,
          name: config.name,
          link: config.link,
          period: period,
          issued_at: new Date()
        }
      }
    }
  );

  return {
    success: true,
    new_balance: user.balance - price,
    subscription_end: newEnd,
    config: config
  };
};
