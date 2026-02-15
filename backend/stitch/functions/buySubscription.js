exports = async function(periodKey) {
  const userId = context.user.id;
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  const PLANS = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
  };

  const plan = PLANS[periodKey];
  if (!plan) {
    throw new Error("Invalid plan period");
  }

  const session = context.services.get("mongodb-atlas").startSession();
  try {
    session.startTransaction();

    // Check balance
    const user = await usersCollection.findOne({ _id: userId.toString() }, { session });
    if (!user) throw new Error("User not found");
    if (user.balance < plan.price) throw new Error("Insufficient balance");

    // Find available config
    // Note: Configs are stored with 'period' matching the key (e.g., '1_month')
    const config = await configsCollection.findOne(
      { period: periodKey, used: false },
      { session }
    );

    if (!config) throw new Error("No configs available for this period");

    // Calculate new subscription end date
    let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
    if (currentEnd < new Date()) currentEnd = new Date(); // If expired, start from now

    const newEnd = new Date(currentEnd);
    newEnd.setDate(newEnd.getDate() + plan.days);

    // Update User
    await usersCollection.updateOne(
      { _id: userId.toString() },
      {
        $inc: { balance: -plan.price },
        $set: { subscription_end: newEnd }
      },
      { session }
    );

    // Update Config
    await configsCollection.updateOne(
      { _id: config._id },
      {
        $set: {
          used: true,
          used_by: userId.toString(),
          used_at: new Date()
        }
      },
      { session }
    );

    await session.commitTransaction();
    session.endSession();

    return { success: true, new_balance: user.balance - plan.price, config_link: config.link };

  } catch (error) {
    await session.abortTransaction();
    session.endSession();
    throw error;
  }
};
