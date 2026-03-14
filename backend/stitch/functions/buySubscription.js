exports = async function(periodKey) {
  const user = context.user;
  if (!user || !user.identities || user.identities.length === 0) {
    throw new Error("User not authenticated properly.");
  }

  // Extract custom identity ID which is the Telegram ID
  const telegramId = user.identities[0].id;

  // Let's parse telegramId to match database type
  let parsedId = parseInt(telegramId);
  if (isNaN(parsedId)) {
    parsedId = telegramId;
  }

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");
  const configsCollection = mongodb.db("vpn_bot").collection("configs");

  const SUBSCRIPTION_PERIODS = {
      '1_month': {'price': 50, 'days': 30},
      '2_months': {'price': 90, 'days': 60},
      '3_months': {'price': 120, 'days': 90}
  };

  const periodData = SUBSCRIPTION_PERIODS[periodKey];
  if (!periodData) {
      return { success: false, message: "Invalid subscription period." };
  }

  const amount = periodData.price;
  const days = periodData.days;

  // 1. Fetch user to check balance
  const userProfile = await usersCollection.findOne({ telegram_id: parsedId }) || await usersCollection.findOne({ telegram_id: telegramId });
  if (!userProfile) {
      return { success: false, message: "User not found." };
  }

  if (userProfile.balance < amount) {
      return { success: false, message: "Insufficient balance." };
  }

  // 2. Atomically reserve a configuration
  const reservedConfig = await configsCollection.findOneAndUpdate(
      { period: periodKey, used: false },
      { $set: { used: true } },
      { returnNewDocument: true }
  );

  if (!reservedConfig) {
      return { success: false, message: "No available configs for this period." };
  }

  // 3. Update user: deduct balance, extend subscription, add config to used_configs
  let currentEnd = userProfile.subscription_end ? new Date(userProfile.subscription_end) : new Date();

  // If subscription has expired, start from now
  const now = new Date();
  if (currentEnd < now) {
      currentEnd = now;
  }

  const newEnd = new Date(currentEnd.getTime() + (days * 24 * 60 * 60 * 1000));

  // Format for Python compatibility (YYYY-MM-DD HH:MM:SS) if needed, or store as ISODate
  // We'll store as ISODate to be MongoDB native, but maybe the old code expected a string.
  // We'll use string format to match legacy JSON representation if needed, but Date is better in Mongo.
  // Using string format for backward compatibility based on legacy code.

  function pad(num) {
    return num.toString().padStart(2, '0');
  }

  const newEndStr = `${newEnd.getFullYear()}-${pad(newEnd.getMonth()+1)}-${pad(newEnd.getDate())} ${pad(newEnd.getHours())}:${pad(newEnd.getMinutes())}:${pad(newEnd.getSeconds())}`;

  const usedConfigEntry = {
      config_name: reservedConfig.name,
      config_link: reservedConfig.link,
      config_code: reservedConfig.code,
      period: periodKey,
      issue_date: `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`,
      user_name: `${userProfile.first_name} (@${userProfile.username})`
  };

  await usersCollection.updateOne(
      { telegram_id: userProfile.telegram_id },
      {
          $inc: { balance: -amount },
          $set: { subscription_end: newEndStr },
          $push: { used_configs: usedConfigEntry }
      }
  );

  return {
      success: true,
      message: "Subscription purchased successfully.",
      config: reservedConfig,
      new_balance: userProfile.balance - amount,
      subscription_end: newEndStr
  };
};
