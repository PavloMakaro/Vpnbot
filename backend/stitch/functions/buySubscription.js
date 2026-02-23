exports = async function(period) {
  const user = context.user;
  const telegramIdentity = user.identities.find(id => id.provider_type === 'custom-function');
  if (!telegramIdentity) throw new Error("User identity not found");
  const telegramId = telegramIdentity.id;

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");
  const configsCollection = mongodb.db("vpn_bot").collection("configs");

  const subscriptionPeriods = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const plan = subscriptionPeriods[period];
  if (!plan) {
    throw new Error("Invalid subscription period");
  }

  // Atomically decrement balance if sufficient funds
  const userUpdate = await usersCollection.findOneAndUpdate(
    { _id: telegramId, balance: { $gte: plan.price } },
    { $inc: { balance: -plan.price } },
    { returnNewDocument: true }
  );

  if (!userUpdate) {
    throw new Error("Insufficient balance");
  }

  // Find available config
  let config = null;
  try {
    config = await configsCollection.findOneAndUpdate(
      { period: period, used: false },
      {
        $set: {
          used: true,
          assigned_to: telegramId,
          assigned_at: new Date()
        }
      },
      { returnNewDocument: true }
    );
  } catch (e) {
      // Config search failed due to DB error
      // Refund
      await usersCollection.updateOne(
        { _id: telegramId },
        { $inc: { balance: plan.price } }
      );
      throw e;
  }

  if (!config) {
    // No config available
    // Refund
    await usersCollection.updateOne(
      { _id: telegramId },
      { $inc: { balance: plan.price } }
    );
    throw new Error("No configs available for this period. Please contact support.");
  }

  try {
      // Calculate new subscription end date based on PREVIOUS state (userUpdate before modification? No, userUpdate is current state)
      // Actually userUpdate reflects balance deduction. It has subscription_end.
      let currentEnd = userUpdate.subscription_end ? new Date(userUpdate.subscription_end) : new Date();
      if (currentEnd < new Date()) {
          currentEnd = new Date();
      }
      const newEnd = new Date(currentEnd.getTime() + plan.days * 24 * 60 * 60 * 1000);

      // Update user subscription details
      await usersCollection.updateOne(
        { _id: telegramId },
        {
          $set: { subscription_end: newEnd },
          $push: {
            used_configs: {
              config_name: config.name,
              config_link: config.link,
              period: period,
              issue_date: new Date()
            }
          }
        }
      );

      return { success: true, new_end_date: newEnd, config: config };

  } catch (error) {
      console.error(`CRITICAL: User ${telegramId} paid for config ${config._id} but profile update failed: ${error}`);
      // In a real system, we'd have a reconciliation process or raise an alert.
      // We do NOT refund here because config is already marked as used/assigned.
      throw new Error("Subscription purchased but profile update failed. Please contact support with ID: " + telegramId);
  }
};
