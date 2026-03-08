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

  const SUBSCRIPTION_PERIODS = {
      '1_month': { price: 50, days: 30 },
      '2_months': { price: 90, days: 60 },
      '3_months': { price: 120, days: 90 }
  };

  return {
    subscription_periods: SUBSCRIPTION_PERIODS,
    used_configs: profile.used_configs || []
  };
};