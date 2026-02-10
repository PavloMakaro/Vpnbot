exports = async function(planId) {
  // Buys a subscription for the user.
  // planId: '1_month', '2_months', etc.

  const client = context.services.get("mongodb-atlas");
  const db = client.db("vpn_bot_db");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  const user = context.user;
  const userId = user.id;

  // Plan details (matching ai_studio_code.py)
  const plans = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const plan = plans[planId];
  if (!plan) {
    throw new Error("Invalid plan ID");
  }

  // Use a transaction for atomicity
  const session = client.startSession();

  try {
    session.startTransaction();

    // 1. Check User Balance
    const userDoc = await usersCollection.findOne({ _id: userId }, { session });

    if (!userDoc) {
      throw new Error("User not found");
    }

    if ((userDoc.balance || 0) < plan.price) {
      throw new Error("Insufficient balance");
    }

    // 2. Find Available Config
    // We look for a config with the matching period that is not used.
    const config = await configsCollection.findOne(
      { period: planId, used: false },
      { session }
    );

    if (!config) {
      throw new Error("No available configs for this period. Please contact support.");
    }

    // 3. Calculate New Subscription End Date
    const now = new Date();
    let currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : null;

    // If subscription ended in the past, reset start time to now.
    if (!currentEnd || currentEnd < now) {
      currentEnd = now;
    }

    const newEnd = new Date(currentEnd);
    newEnd.setDate(newEnd.getDate() + plan.days);

    // 4. Update User: deduct balance, set subscription, add to history
    await usersCollection.updateOne(
      { _id: userId },
      {
        $inc: { balance: -plan.price },
        $set: { subscription_end: newEnd },
        $push: { used_configs: {
            config_name: config.name,
            config_link: config.link,
            config_code: config.code,
            period: planId,
            issue_date: now
        }}
      },
      { session }
    );

    // 5. Update Config: mark as used
    await configsCollection.updateOne(
      { _id: config._id },
      { $set: { used: true, assigned_to: userId, assigned_at: now } },
      { session }
    );

    await session.commitTransaction();

    return {
      success: true,
      message: "Subscription purchased successfully",
      new_balance: (userDoc.balance || 0) - plan.price,
      subscription_end: newEnd,
      config: {
          link: config.link,
          code: config.code,
          name: config.name
      }
    };

  } catch (err) {
    await session.abortTransaction();
    console.error("Purchase transaction failed:", err);
    throw err; // Rethrow to let the caller know
  } finally {
    session.endSession();
  }
};
