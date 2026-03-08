exports = async function(periodKey) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("User not authenticated");
  }

  const telegramId = user.id;

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");
  const configsCollection = mongodb.db("vpn_bot").collection("configs");

  const SUBSCRIPTION_PERIODS = {
      '1_month': { price: 50, days: 30 },
      '2_months': { price: 90, days: 60 },
      '3_months': { price: 120, days: 90 }
  };

  const periodData = SUBSCRIPTION_PERIODS[periodKey];
  if (!periodData) {
    throw new Error("Invalid subscription period");
  }

  const amount = periodData.price;
  const days = periodData.days;

  const profile = await usersCollection.findOne({ _id: telegramId });

  if (!profile) {
    throw new Error("Profile not found");
  }

  if (profile.balance < amount) {
    return { success: false, error: "Insufficient balance" };
  }

  // Atomically reserve a config
  const reservedConfig = await configsCollection.findOneAndUpdate(
    { period: periodKey, used: false },
    { $set: { used: true } },
    { returnNewDocument: true }
  );

  if (!reservedConfig) {
    return { success: false, error: "No available configs for this period" };
  }

  let currentEnd = profile.subscription_end;
  let newEnd;

  if (currentEnd) {
    const end = new Date(currentEnd);
    if (end > new Date()) {
        newEnd = new Date(end.getTime() + days * 24 * 60 * 60 * 1000);
    } else {
        newEnd = new Date(new Date().getTime() + days * 24 * 60 * 60 * 1000);
    }
  } else {
    newEnd = new Date(new Date().getTime() + days * 24 * 60 * 60 * 1000);
  }

  // Format the date to match legacy YYYY-MM-DD HH:MM:SS format
  const pad = (n) => n < 10 ? '0' + n : n;
  const newEndFormatted = `${newEnd.getFullYear()}-${pad(newEnd.getMonth()+1)}-${pad(newEnd.getDate())} ${pad(newEnd.getHours())}:${pad(newEnd.getMinutes())}:${pad(newEnd.getSeconds())}`;

  const issueDateFormatted = `${new Date().getFullYear()}-${pad(new Date().getMonth()+1)}-${pad(new Date().getDate())} ${pad(new Date().getHours())}:${pad(new Date().getMinutes())}:${pad(new Date().getSeconds())}`;


  const usedConfig = {
      config_name: reservedConfig.name,
      config_link: reservedConfig.link,
      config_code: reservedConfig.code,
      period: periodKey,
      issue_date: issueDateFormatted,
      user_name: `${profile.first_name} (@${profile.username})`
  };

  // Update user profile
  await usersCollection.updateOne(
    { _id: telegramId },
    {
      $inc: { balance: -amount },
      $set: { subscription_end: newEndFormatted },
      $push: { used_configs: usedConfig }
    }
  );

  return { success: true, config: usedConfig, new_balance: profile.balance - amount, new_end: newEndFormatted };
};