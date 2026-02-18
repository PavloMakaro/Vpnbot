exports = async function(arg) {
  const period = arg.period;
  if (!period) throw new Error("Period is required");

  const user = context.user;
  if (!user) throw new Error("User not authenticated");
  const userId = user.id;

  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  const SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
  };

  const plan = SUBSCRIPTION_PERIODS[period];
  if (!plan) throw new Error("Invalid period");

  // Transaction-like logic (MongoDB Atlas supports transactions, but for simplicity we use sequential checks with potential race conditions handled by findOneAndUpdate)

  // 1. Get User Balance
  const userDoc = await usersCollection.findOne({ _id: userId });
  if (!userDoc) throw new Error("User not found");

  if (userDoc.balance < plan.price) {
    throw new Error("Insufficient balance");
  }

  // 2. Find and Reserve Config
  // We use findOneAndUpdate to atomically pick an unused config
  const config = await configsCollection.findOneAndUpdate(
    { period: period, used: false },
    { $set: { used: true, owner: userId, assigned_at: new Date() } },
    { returnNewDocument: true }
  );

  if (!config) {
    throw new Error("No configs available for this period");
  }

  // 3. Deduct Balance and Update Subscription
  const currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : new Date();
  const now = new Date();
  const startDate = currentEnd > now ? currentEnd : now;
  const newEnd = new Date(startDate.getTime() + (plan.days * 24 * 60 * 60 * 1000));

  await usersCollection.updateOne(
    { _id: userId },
    {
      $inc: { balance: -plan.price },
      $set: { subscription_end: newEnd },
      $push: { used_configs: config }
    }
  );

  return { success: true, config: config, new_balance: userDoc.balance - plan.price, subscription_end: newEnd };
};
