exports = async function(period) {
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  // Use Authenticated User ID
  const userId = context.user.id;
  if (!userId) return { error: "Not authenticated" };

  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  if (!SUBSCRIPTION_PERIODS[period]) {
    return { error: "Invalid period" };
  }

  const { price, days } = SUBSCRIPTION_PERIODS[period];

  // 1. Check User Balance (Preliminary)
  const user = await usersCollection.findOne({ _id: userId });
  if (!user) return { error: "User not found" };
  if (user.balance < price) return { error: "Insufficient balance" };

  // 2. Reserve Config
  const config = await configsCollection.findOneAndUpdate(
    { period: period, used: false, reserved_by: { $exists: false } },
    { $set: { reserved_by: userId, reserved_at: new Date() } },
    { returnNewDocument: true }
  );

  if (!config) {
    return { error: "No configs available for this period. Please contact support." };
  }

  // 3. Deduct Balance and Update User
  const now = new Date();
  let currentEnd = user.subscription_end ? new Date(user.subscription_end) : now;
  if (currentEnd < now) currentEnd = now;

  const newEnd = new Date(currentEnd);
  newEnd.setDate(newEnd.getDate() + days);

  const newConfigEntry = {
    config_name: config.name || `VPN ${days} days`,
    config_link: config.link,
    config_code: config.code,
    period: period,
    issue_date: now.toISOString().split('T')[0]
  };

  const updatedUser = await usersCollection.findOneAndUpdate(
    { _id: userId, balance: { $gte: price } },
    {
      $inc: { balance: -price },
      $set: { subscription_end: newEnd },
      $push: { used_configs: newConfigEntry }
    },
    { returnNewDocument: true }
  );

  if (!updatedUser) {
    // Rollback: Unreserve config
    await configsCollection.updateOne(
        { _id: config._id },
        { $unset: { reserved_by: "", reserved_at: "" } }
    );
    return { error: "Insufficient balance (transaction failed)" };
  }

  // 4. Finalize Config
  await configsCollection.updateOne(
    { _id: config._id },
    { $set: { used: true, used_by: userId, used_at: now } }
  );

  // 5. Send Notification
  try {
     const BOT_TOKEN = context.values.get("BOT_TOKEN");
     if (BOT_TOKEN) {
         await context.http.post({
            url: `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`,
            body: {
                chat_id: userId,
                text: `✅ Подписка успешно оформлена!\n📅 Истекает: ${newEnd.toLocaleDateString()}\n🔑 Ваш конфиг доступен в приложении.`
            },
            encodeBodyAsJSON: true
         });
     }
  } catch(e) {}

  return { success: true, user: updatedUser };
};
