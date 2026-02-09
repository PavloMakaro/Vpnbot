exports = async function(planId) {
  const user = context.user;
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  if (!SUBSCRIPTION_PERIODS[planId]) {
    throw new Error("Invalid plan ID");
  }

  const plan = SUBSCRIPTION_PERIODS[planId];
  const userDoc = await usersCollection.findOne({ _id: user.id });

  if (!userDoc) {
    throw new Error("User not found");
  }

  if (userDoc.balance < plan.price) {
    throw new Error("Insufficient balance");
  }

  // Find an available config for the period
  const config = await configsCollection.findOne({
    period: planId,
    used: false
  });

  if (!config) {
    throw new Error("No available configs for this period. Please contact support.");
  }

  // Update user balance and subscription
  let currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : new Date();
  if (currentEnd < new Date()) {
    currentEnd = new Date();
  }

  const newEnd = new Date(currentEnd.getTime() + plan.days * 24 * 60 * 60 * 1000);

  // Mark config as used
  await configsCollection.updateOne(
    { _id: config._id },
    { $set: { used: true, assigned_to: user.id, assigned_at: new Date() } }
  );

  // Update user
  const assignedConfig = {
    config_name: config.name,
    config_link: config.link,
    config_code: config.code,
    period: planId,
    issue_date: new Date().toISOString(),
    user_name: userDoc.username
  };

  await usersCollection.updateOne(
    { _id: user.id },
    {
      $inc: { balance: -plan.price },
      $set: { subscription_end: newEnd.toISOString() },
      $push: { used_configs: assignedConfig }
    }
  );

  return {
    success: true,
    new_balance: userDoc.balance - plan.price,
    subscription_end: newEnd,
    config: assignedConfig
  };
};
