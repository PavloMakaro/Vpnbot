exports = async function(periodKey) {
  const user = context.user;
  if (!user) throw new Error("Unauthorized");

  const identity = user.identities.find(id => id.provider_type === 'custom-function');
  const telegramId = identity ? identity.id : user.id;

  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  const userDoc = await usersCollection.findOne({ _id: telegramId });

  // 1. Get Price
  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const plan = SUBSCRIPTION_PERIODS[periodKey];
  if (!plan) throw new Error("Invalid plan");

  if ((userDoc.balance || 0) < plan.price) {
    throw new Error("Insufficient balance");
  }

  // 2. Find available config
  const config = await configsCollection.findOneAndUpdate(
    { period: periodKey, used: false },
    { $set: { used: true, used_by: telegramId, used_at: new Date() } },
    { returnNewDocument: true }
  );

  if (!config) {
    throw new Error("No configs available for this period. Contact support.");
  }

  // 3. Deduct balance and update subscription
  let currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : new Date();
  if (currentEnd < new Date()) currentEnd = new Date(); // If expired, start from now

  const newEnd = new Date(currentEnd.getTime() + (plan.days * 24 * 60 * 60 * 1000));

  await usersCollection.updateOne(
    { _id: telegramId },
    {
      $inc: { balance: -plan.price },
      $set: { subscription_end: newEnd },
      $push: {
        used_configs: {
          config_name: config.name,
          config_link: config.link,
          period: periodKey,
          issue_date: new Date()
        }
      }
    }
  );

  return {
    success: true,
    new_balance: (userDoc.balance - plan.price),
    subscription_end: newEnd,
    config: config.link
  };
};
