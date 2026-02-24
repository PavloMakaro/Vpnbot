exports = async function(period) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("Unauthorized");
  }

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  const SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30},
    '2_months': {'price': 90, 'days': 60},
    '3_months': {'price': 120, 'days': 90}
  };

  const periodData = SUBSCRIPTION_PERIODS[period];
  if (!periodData) {
    throw new Error("Invalid subscription period");
  }
  const { price, days } = periodData;

  // 1. Optimistic balance check
  const userDoc = await usersCollection.findOne({ _id: user.id });
  if (!userDoc || (userDoc.balance || 0) < price) {
    throw new Error("Insufficient balance");
  }

  // 2. Reserve a config
  const config = await configsCollection.findOneAndUpdate(
    { period: period, used: false },
    { $set: { used: true, user_id: user.id, used_at: new Date() } },
    { returnNewDocument: true }
  );

  if (!config) {
    throw new Error("No available configs for this period");
  }

  // Calculate new subscription end date
  let currentEnd = userDoc.subscription_end;
  let newEndDate = new Date();
  if (currentEnd && new Date(currentEnd) > new Date()) {
    newEndDate = new Date(currentEnd);
  }
  newEndDate.setDate(newEndDate.getDate() + days);

  // 3. Deduct balance and assign config
  const updateResult = await usersCollection.updateOne(
    { _id: user.id, balance: { $gte: price } },
    {
      $inc: { balance: -price },
      $set: { subscription_end: newEndDate },
      $push: {
        used_configs: {
          config_name: config.name || `Config ${period}`,
          config_link: config.link,
          config_code: config.code,
          period: period,
          issue_date: new Date(),
          user_name: userDoc.first_name || userDoc.username
        }
      }
    }
  );

  if (updateResult.modifiedCount !== 1) {
    // 4. Rollback config if balance deduction failed
    await configsCollection.updateOne(
      { _id: config._id },
      { $set: { used: false, user_id: null, used_at: null } }
    );
    throw new Error("Insufficient balance or transaction failed");
  }

  return {
    success: true,
    new_balance: (userDoc.balance || 0) - price,
    subscription_end: newEndDate
  };
};
