exports = async function(arg) {
  const { period } = arg;
  const user = context.user;
  const userId = user.id;

  const PRICES = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const plan = PRICES[period];
  if (!plan) {
    throw new Error("Invalid period");
  }

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const users = db.collection("users");
  const configs = db.collection("configs");

  // 1. Atomically Check Balance and Deduct
  const result = await users.updateOne(
    { _id: userId, balance: { $gte: plan.price } },
    { $inc: { balance: -plan.price } }
  );

  if (result.modifiedCount === 0) {
    throw new Error("Insufficient balance or user not found");
  }

  // 2. Find and Reserve Config Atomically
  const config = await configs.findOneAndUpdate(
    { period: period, used: false },
    {
      $set: {
        used: true,
        used_by: userId,
        used_at: new Date()
      }
    },
    { returnNewDocument: true }
  );

  if (!config) {
    // Rollback Balance (Critical!)
    await users.updateOne(
      { _id: userId },
      { $inc: { balance: plan.price } }
    );
    throw new Error("No available configs for this period. Balance refunded.");
  }

  // 3. Update Subscription End Date
  const userDoc = await users.findOne({ _id: userId });
  const now = new Date();
  let currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : now;
  if (currentEnd < now) currentEnd = now;

  const newEnd = new Date(currentEnd);
  newEnd.setDate(newEnd.getDate() + plan.days);

  const newConfigEntry = {
    config_name: config.name,
    config_link: config.link,
    config_code: config.code,
    period: period,
    issue_date: new Date(),
    expiry_date: newEnd
  };

  await users.updateOne(
    { _id: userId },
    {
      $set: { subscription_end: newEnd },
      $push: { used_configs: newConfigEntry }
    }
  );

  return {
    success: true,
    config: newConfigEntry,
    new_balance: userDoc.balance // Note: this is balance BEFORE refund if rolled back, but here successful
  };
};
