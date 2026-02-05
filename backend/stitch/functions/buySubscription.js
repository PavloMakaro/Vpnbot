exports = async function(periodKey) {
  const user = context.user;
  if (!user) throw new Error("Not authenticated");

  const telegramId = user.custom_data.telegram_id;
  const mongodb = context.services.get("mongodb-atlas");
  const db = mongodb.db("vpn_bot");
  const users = db.collection("users");
  const configs = db.collection("configs");

  const plans = context.functions.execute("getAvailablePlans");
  const plan = plans[periodKey];

  if (!plan) throw new Error("Invalid plan");

  // Transaction logic
  const session = mongodb.startSession();
  try {
    session.startTransaction();

    const userDoc = await users.findOne({ _id: telegramId }, { session });

    if (userDoc.balance < plan.price) {
      throw new Error("Insufficient balance");
    }

    // Find an unused config for this period
    // Note: In the original code, configs are stored in JSON by period.
    // In MongoDB, we assume 'configs' collection has 'period' field and 'used' boolean.
    const config = await configs.findOneAndUpdate(
      { period: periodKey, used: false },
      { $set: { used: true, assigned_to: telegramId, assigned_at: new Date() } },
      { session, returnNewDocument: true }
    );

    if (!config) {
      throw new Error("No available configs for this period. Contact support.");
    }

    // Update user balance and subscription
    let currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : new Date();
    if (currentEnd < new Date()) currentEnd = new Date();

    currentEnd.setDate(currentEnd.getDate() + plan.days);

    const usedConfigEntry = {
        config_name: config.name,
        config_link: config.link,
        config_code: config.code,
        period: periodKey,
        issue_date: new Date(),
        user_name: userDoc.first_name
    };

    await users.updateOne(
      { _id: telegramId },
      {
        $inc: { balance: -plan.price },
        $set: { subscription_end: currentEnd },
        $push: { used_configs: usedConfigEntry }
      },
      { session }
    );

    await session.commitTransaction();
    return { success: true, message: "Subscription purchased", config: config.link, subscription_end: currentEnd };

  } catch (e) {
    await session.abortTransaction();
    throw e;
  } finally {
    session.endSession();
  }
};
