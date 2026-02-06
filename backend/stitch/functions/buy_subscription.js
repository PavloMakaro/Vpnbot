exports = async function(periodKey) {
  const plans = context.functions.execute("getPlans");
  const plan = plans[periodKey];

  if (!plan) {
    throw new Error("Invalid plan");
  }

  const user = context.user;
  const userId = user.id;
  const price = plan.price;
  const days = plan.days;

  const mongodb = context.services.get("mongodb-atlas");
  const db = mongodb.db("vpn_bot");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  // Transaction-like logic (MongoDB Atlas supports transactions if cluster is replica set)
  // For simplicity, we'll do checks and updates.

  const userDoc = await usersCollection.findOne({ _id: userId });
  if (!userDoc || userDoc.balance < price) {
    return { success: false, error: "Insufficient balance" };
  }

  // Find an available config
  // We need to match the period if configs are segregated by period
  // Assuming configs collection has a 'period' field matching plan keys
  const config = await configsCollection.findOneAndUpdate(
    { period: periodKey, used: false },
    { $set: { used: true, used_by: userId, used_at: new Date() } }
  );

  if (!config) {
    return { success: false, error: "No available configs for this period. Contact support." };
  }

  // Update User Balance and Subscription
  let currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : new Date();
  if (currentEnd < new Date()) {
    currentEnd = new Date();
  }

  const newEnd = new Date(currentEnd.getTime() + days * 24 * 60 * 60 * 1000);

  const configRecord = {
    config_name: config.name,
    config_link: config.link,
    config_code: config.code,
    period: periodKey,
    issue_date: new Date().toISOString(),
    // ... other metadata
  };

  await usersCollection.updateOne(
    { _id: userId },
    {
      $inc: { balance: -price },
      $set: { subscription_end: newEnd.toISOString() },
      $push: { used_configs: configRecord }
    }
  );

  return { success: true, new_balance: userDoc.balance - price, subscription_end: newEnd };
};
