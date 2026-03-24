exports = async function() {
  const telegramId = context.user.identities[0].id; // Extract as string

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  const user = await usersCollection.findOne({ telegram_id: telegramId });
  if (!user) {
    throw new Error("User not found in database.");
  }

  return {
    telegram_id: user.telegram_id,
    username: user.username,
    first_name: user.first_name,
    balance: user.balance || 0,
    subscription_end: user.subscription_end || null,
    used_configs: user.used_configs || [],
    referrals_count: user.referrals_count || 0
  };
};
