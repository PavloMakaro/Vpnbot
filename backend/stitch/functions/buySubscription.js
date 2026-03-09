exports = async function(telegramId, periodKey) {
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersColl = db.collection("users");
  const configsColl = db.collection("configs");

  const SUBSCRIPTION_PERIODS = {
      '1_month': { price: 50, days: 30 },
      '2_months': { price: 90, days: 60 },
      '3_months': { price: 120, days: 90 }
  };

  const periodData = SUBSCRIPTION_PERIODS[periodKey];
  if (!periodData) {
      return { success: false, message: "Invalid subscription period." };
  }

  const user = await usersColl.findOne({ _id: telegramId });
  if (!user) {
      return { success: false, message: "User not found." };
  }

  if (user.balance < periodData.price) {
      return { success: false, message: "Insufficient balance." };
  }

  // Atomically find an unused config and mark it as used
  const config = await configsColl.findOneAndUpdate(
      { period: periodKey, used: false },
      { $set: { used: true } },
      { returnNewDocument: true }
  );

  if (!config) {
      return { success: false, message: "No available configurations for this period." };
  }

  // Calculate new subscription end date
  let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
  const now = new Date();
  if (currentEnd < now) {
      currentEnd = now;
  }

  const newEnd = new Date(currentEnd.getTime() + (periodData.days * 24 * 60 * 60 * 1000));

  const usedConfigEntry = {
      config_name: config.name,
      config_link: config.link,
      config_code: config.code || "",
      period: periodKey,
      issue_date: now.toISOString().replace('T', ' ').substring(0, 19),
      user_name: `${user.first_name} (@${user.username})`
  };

  // Deduct balance and update user
  const newBalance = user.balance - periodData.price;

  await usersColl.updateOne(
      { _id: telegramId },
      {
          $set: {
              balance: newBalance,
              subscription_end: newEnd.toISOString().replace('T', ' ').substring(0, 19)
          },
          $push: {
              used_configs: usedConfigEntry
          }
      }
  );

  return {
      success: true,
      message: "Subscription purchased successfully!",
      config: usedConfigEntry,
      new_balance: newBalance,
      subscription_end: newEnd.toISOString().replace('T', ' ').substring(0, 19)
  };
};