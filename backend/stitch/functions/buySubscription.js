exports = async function(period) {
  const userId = context.user.id;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const users = db.collection("users");
  const configs = db.collection("configs");

  // 1. Get Price Info
  const PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const plan = PERIODS[period];
  if (!plan) {
    throw new Error("Invalid period");
  }

  // 2. Deduct Balance (Atomic check & update)
  const userUpdate = await users.findOneAndUpdate(
    { _id: userId, balance: { $gte: plan.price } },
    { $inc: { balance: -plan.price } },
    { returnNewDocument: true }
  );

  if (!userUpdate) {
    throw new Error("Insufficient funds");
  }

  // 3. Assign Config (Atomic find & update)
  const configUpdate = await configs.findOneAndUpdate(
    { period: period, used: false },
    {
      $set: {
        used: true,
        assigned_to: userId,
        assigned_at: new Date()
      }
    },
    { returnNewDocument: true }
  );

  if (!configUpdate) {
    // Refund user if no config available
    await users.updateOne(
      { _id: userId },
      { $inc: { balance: plan.price } }
    );
    throw new Error("No configs available for this period. Balance refunded.");
  }

  // 4. Update User Subscription Expiry
  let currentEnd = userUpdate.subscription_end ? new Date(userUpdate.subscription_end) : new Date();
  if (currentEnd < new Date()) {
      currentEnd = new Date();
  }
  currentEnd.setDate(currentEnd.getDate() + plan.days);

  await users.updateOne(
      { _id: userId },
      {
          $set: { subscription_end: currentEnd },
          // Store history in user doc as well for redundancy/easier access if needed
          $push: {
              used_configs: {
                  config_id: configUpdate._id,
                  period: period,
                  issue_date: new Date(),
                  name: configUpdate.name || "Config"
              }
          }
      }
  );

  return {
    status: "success",
    config: configUpdate,
    new_subscription_end: currentEnd
  };
};
