exports = async function(planId) {
  const user = context.user;
  const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const plans = context.services.get("mongodb-atlas").db("vpn_bot").collection("plans");
  const configs = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  const session = context.services.get("mongodb-atlas").startSession();

  try {
    session.startTransaction();

    // 1. Get User
    const userDoc = await users.findOne({ _id: user.id }, { session });
    if (!userDoc) throw new Error("User not found");

    // 2. Get Plan
    const planDoc = await plans.findOne({ _id: planId }, { session });
    if (!planDoc) throw new Error("Plan not found");

    // 3. Check Balance
    if (userDoc.balance < planDoc.price) {
      throw new Error("Insufficient balance");
    }

    // 4. Find Available Config
    // This assumes configs are pre-populated and marked as used=false
    const configDoc = await configs.findOneAndUpdate(
      { period: planId, used: false },
      { $set: { used: true, assigned_to: user.id, assigned_at: new Date() } },
      { session, returnNewDocument: true }
    );

    if (!configDoc) {
      throw new Error("No available configs for this plan. Please contact support.");
    }

    // 5. Update User Balance and Subscription
    const currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : new Date();
    // If subscription ended in the past, start from now
    const startDate = currentEnd > new Date() ? currentEnd : new Date();
    const newEnd = new Date(startDate.getTime() + (planDoc.days * 24 * 60 * 60 * 1000));

    const usedConfigEntry = {
      config_name: configDoc.name,
      config_link: configDoc.link,
      period: planId,
      issue_date: new Date(),
      user_name: userDoc.first_name
    };

    await users.updateOne(
      { _id: user.id },
      {
        $inc: { balance: -planDoc.price },
        $set: { subscription_end: newEnd },
        $push: { used_configs: usedConfigEntry }
      },
      { session }
    );

    await session.commitTransaction();
    session.endSession();

    return { success: true, new_balance: userDoc.balance - planDoc.price, config: usedConfigEntry };

  } catch (error) {
    await session.abortTransaction();
    session.endSession();
    throw error;
  }
};
