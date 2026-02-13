exports = async function(period){
  const user = context.user;
  if (!user) {
    throw new Error("User not authenticated");
  }

  const userId = user.id;
  const db = context.services.get("mongodb-atlas").db("vpn_bot_db");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  // Define plans (hardcoded for now as per Python code, or could fetch from DB)
  const SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
  };

  const plan = SUBSCRIPTION_PERIODS[period];
  if (!plan) {
    throw new Error("Invalid plan period");
  }

  const session = context.services.get("mongodb-atlas").startSession();

  try {
    session.startTransaction();

    // 1. Check user balance
    const userDoc = await usersCollection.findOne({ _id: userId }, { session });
    if (!userDoc) {
      throw new Error("User not found");
    }

    if (userDoc.balance < plan.price) {
      throw new Error("Insufficient balance");
    }

    // 2. Find available config
    const config = await configsCollection.findOne({
      period: period,
      used: { $ne: true }
    }, { session });

    if (!config) {
      throw new Error("No available configs for this period. Please contact support.");
    }

    // 3. Deduct balance and update subscription
    let currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : new Date();
    if (currentEnd < new Date()) {
      currentEnd = new Date();
    }
    const newEnd = new Date(currentEnd.getTime() + plan.days * 24 * 60 * 60 * 1000);

    const usedConfigEntry = {
      config_name: config.name,
      config_link: config.link,
      config_code: config.code,
      period: period,
      issue_date: new Date().toISOString(),
      user_name: `${userDoc.first_name} (@${userDoc.username})`
    };

    await usersCollection.updateOne(
      { _id: userId },
      {
        $inc: { balance: -plan.price },
        $set: { subscription_end: newEnd.toISOString() },
        $push: { used_configs: usedConfigEntry }
      },
      { session }
    );

    // 4. Mark config as used
    await configsCollection.updateOne(
      { _id: config._id },
      { $set: { used: true, assigned_to: userId, assigned_at: new Date() } },
      { session }
    );

    await session.commitTransaction();

    return {
      success: true,
      message: "Subscription purchased successfully",
      config: usedConfigEntry,
      new_balance: userDoc.balance - plan.price,
      subscription_end: newEnd.toISOString()
    };

  } catch (err) {
    await session.abortTransaction();
    throw err;
  } finally {
    session.endSession();
  }
};
