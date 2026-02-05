exports = async function() {
  const user = context.user;
  if (!user) throw new Error("Not authenticated");

  const telegramId = user.custom_data.telegram_id;
  if (!telegramId) throw new Error("No telegram_id in custom_data");

  const mongodb = context.services.get("mongodb-atlas");
  const users = mongodb.db("vpn_bot").collection("users");

  let userDoc = await users.findOne({ _id: telegramId });

  if (!userDoc) {
    // Initial creation if not exists
    userDoc = {
      _id: telegramId,
      balance: 0,
      username: user.custom_data.username,
      first_name: user.custom_data.first_name,
      referrals_count: 0,
      subscription_end: null,
      used_configs: []
    };
    await users.insertOne(userDoc);
  }

  // Calculate days left
  let days_left = 0;
  if (userDoc.subscription_end) {
    const end = new Date(userDoc.subscription_end);
    const now = new Date();
    if (end > now) {
      const diffTime = Math.abs(end - now);
      days_left = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }
  }

  userDoc.days_left = days_left;
  return userDoc;
};
