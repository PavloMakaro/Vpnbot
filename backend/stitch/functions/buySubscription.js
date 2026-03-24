exports = async function(periodKey) {
  const telegramId = context.user.identities[0].id;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");

  // 1. Validate period
  const periods = context.functions.execute("getConfigs");
  if (!periods[periodKey]) {
    return { success: false, message: "Invalid subscription period." };
  }

  const amount = periods[periodKey].price;
  const addDays = periods[periodKey].days;

  // 2. Fetch User and Check Balance
  const user = await db.collection("users").findOne({ telegram_id: telegramId });
  if (!user) {
    return { success: false, message: "User not found." };
  }

  const balance = user.balance || 0;
  if (balance < amount) {
    return { success: false, message: "Insufficient balance.", needTopUp: amount - balance };
  }

  // 3. Atomically Reserve Config (to prevent race conditions)
  const updateResult = await db.collection("configs").findOneAndUpdate(
    { period: periodKey, used: false },
    { $set: { used: true } },
    { returnNewDocument: true }
  );

  // Fallback check if findOneAndUpdate did not find one
  const config = updateResult;
  if (!config) {
     return { success: false, message: "No available configurations for this period. Please contact support." };
  }

  // 4. Calculate New Subscription End Date
  let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
  if (currentEnd < new Date()) {
      currentEnd = new Date();
  }

  const newEnd = new Date(currentEnd.getTime() + addDays * 24 * 60 * 60 * 1000);

  // Format dates consistently
  const issueDateStr = new Date().toISOString().replace('T', ' ').substring(0, 19);
  const newEndStr = newEnd.toISOString().replace('T', ' ').substring(0, 19);

  // 5. Build Used Config Record
  const usedConfig = {
      config_name: config.name,
      config_link: config.link,
      config_code: config.code || "",
      period: periodKey,
      issue_date: issueDateStr,
      user_name: `${user.first_name} (@${user.username})`
  };

  // 6. Deduct Balance, Update Sub, and Push Config
  await db.collection("users").updateOne(
    { telegram_id: telegramId },
    {
      $inc: { balance: -amount },
      $set: { subscription_end: newEndStr },
      $push: { used_configs: usedConfig }
    }
  );

  return {
    success: true,
    message: "Subscription purchased successfully!",
    config: usedConfig,
    newBalance: balance - amount,
    subscriptionEnd: newEndStr
  };
};