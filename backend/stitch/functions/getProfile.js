exports = async function() {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("User not authenticated");
  }

  const telegramId = user.id;

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  const profile = await usersCollection.findOne({ _id: telegramId });

  if (!profile) {
    throw new Error("Profile not found");
  }

  return {
    id: profile._id,
    username: profile.username,
    first_name: profile.first_name,
    balance: profile.balance,
    subscription_end: profile.subscription_end,
    referrals_count: profile.referrals_count,
    used_configs: profile.used_configs
  };
};