exports = async function({ planId }) {
  const userId = context.user.id;
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  // Subscription Plans
  const PLANS = {
    "1_month": { price: 50, days: 30 },
    "2_months": { price: 90, days: 60 },
    "3_months": { price: 120, days: 90 }
  };

  const plan = PLANS[planId];
  if (!plan) {
    return { success: false, message: "Invalid plan ID" };
  }

  const session = context.services.get("mongodb-atlas").startSession();
  session.startTransaction();

  try {
    // 1. Check User Balance
    const user = await usersCollection.findOne({ user_id: userId }, { session });
    if (!user || user.balance < plan.price) {
      await session.abortTransaction();
      return { success: false, message: "Insufficient balance" };
    }

    // 2. Find Available Config for the period
    const config = await configsCollection.findOneAndUpdate(
      { period: planId, used: false },
      { $set: { used: true, user_id: userId, assigned_at: new Date() } },
      { returnNewDocument: true, session }
    );

    if (!config) {
      await session.abortTransaction();
      return { success: false, message: "No available configs for this period. Please contact support." };
    }

    // 3. Update User Balance & Subscription
    const currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
    const newEnd = new Date(Math.max(currentEnd.getTime(), Date.now()) + plan.days * 24 * 60 * 60 * 1000);

    await usersCollection.updateOne(
      { user_id: userId },
      {
        $inc: { balance: -plan.price },
        $set: { subscription_end: newEnd },
        $push: {
          used_configs: {
            config_name: config.name,
            config_link: config.link,
            period: planId,
            issue_date: new Date()
          }
        }
      },
      { session }
    );

    await session.commitTransaction();
    return { success: true, message: "Subscription purchased successfully!" };

  } catch (err) {
    await session.abortTransaction();
    console.error("Purchase Error:", err);
    return { success: false, message: "An error occurred during purchase." };
  } finally {
    session.endSession();
  }
};
