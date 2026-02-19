exports = async function(period) {
  const mongodb = context.services.get("mongodb-atlas");
  const db = mongodb.db("vpn_bot");
  const users = db.collection("users");
  const configs = db.collection("configs");
  const settings = db.collection("settings");

  const userId = context.user.id;

  // 1. Get Pricing
  let pricing = {
    "1_month": { "price": 50, "days": 30 },
    "2_months": { "price": 90, "days": 60 },
    "3_months": { "price": 120, "days": 90 }
  };

  try {
    const settingsDoc = await settings.findOne({ _id: "pricing" });
    if (settingsDoc && settingsDoc.periods) {
      pricing = settingsDoc.periods;
    }
  } catch (e) { console.error(e); }

  const plan = pricing[period];
  if (!plan) {
    throw new Error("Invalid period");
  }

  // 2. Check Balance & Stock Check (Optimistic)
  const user = await users.findOne({ _id: userId });
  if (!user) throw new Error("User not found");
  if (user.balance < plan.price) throw new Error("Insufficient balance");

  const availableConfigCount = await configs.count({ period: period, used: false });
  if (availableConfigCount === 0) throw new Error("Out of stock");

  // 3. Deduct Balance (Atomic check)
  const deductResult = await users.updateOne(
    { _id: userId, balance: { $gte: plan.price } },
    { $inc: { balance: -plan.price } }
  );

  if (deductResult.modifiedCount === 0) {
    throw new Error("Insufficient balance or transaction failed");
  }

  // 4. Assign Config
  const config = await configs.findOneAndUpdate(
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

  if (!config) {
    // Refund if assignment failed (race condition)
    await users.updateOne(
      { _id: userId },
      { $inc: { balance: plan.price } }
    );
    throw new Error("Out of stock (Refunded)");
  }

  // 5. Extend Subscription
  let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
  if (currentEnd < new Date()) {
      currentEnd = new Date();
  }
  const newSubEnd = new Date(currentEnd.getTime() + (plan.days * 24 * 60 * 60 * 1000));

  await users.updateOne(
    { _id: userId },
    { $set: { subscription_end: newSubEnd } }
  );

  return {
    success: true,
    message: "Subscription active",
    config: config,
    subscription_end: newSubEnd
  };
};
