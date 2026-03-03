exports = async function(periodKey) {
  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  if (!SUBSCRIPTION_PERIODS[periodKey]) {
    throw new Error("Invalid subscription period");
  }

  const periodData = SUBSCRIPTION_PERIODS[periodKey];
  const price = periodData.price;
  const addDays = periodData.days;

  const mongodb = context.services.get("mongodb-atlas");
  const db = mongodb.db("vpn");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");

  const userId = context.user.id;

  // 1. Check user balance
  const user = await usersCollection.findOne({ _id: userId });
  if (!user) {
    throw new Error("User not found");
  }

  const currentBalance = user.balance || 0;
  if (currentBalance < price) {
    throw new Error("Insufficient balance");
  }

  // 2. Atomically reserve a configuration
  // Find a config for the given period where used is false or missing
  const reservedConfig = await configsCollection.findOneAndUpdate(
    {
        period: periodKey,
        $or: [{ used: false }, { used: { $exists: false } }]
    },
    { $set: { used: true } },
    { returnNewDocument: true }
  );

  if (!reservedConfig) {
    throw new Error("No available configs for this period");
  }

  // 3. Deduct balance and update subscription end date
  let newEndDate = new Date();
  if (user.subscription_end) {
      const currentEnd = new Date(user.subscription_end);
      if (currentEnd > newEndDate) {
          newEndDate = currentEnd;
      }
  }
  newEndDate.setDate(newEndDate.getDate() + addDays);

  const usedConfigEntry = {
      config_name: reservedConfig.name,
      config_link: reservedConfig.link,
      config_code: reservedConfig.code || null,
      period: periodKey,
      issue_date: new Date(),
      user_name: `${user.first_name || 'User'} (@${user.username || 'user'})`
  };

  await usersCollection.updateOne(
    { _id: userId },
    {
        $inc: { balance: -price },
        $set: { subscription_end: newEndDate },
        $push: { used_configs: usedConfigEntry }
    }
  );

  return {
    success: true,
    newBalance: currentBalance - price,
    subscriptionEnd: newEndDate,
    config: {
        name: reservedConfig.name,
        link: reservedConfig.link,
        code: reservedConfig.code,
        period: periodKey
    }
  };
};