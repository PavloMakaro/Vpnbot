exports = async function() {
  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn").collection("users");

  const userId = context.user.id;
  const user = await usersCollection.findOne({ _id: userId });

  return {
    subscriptionPeriods: SUBSCRIPTION_PERIODS,
    userBalance: user ? (user.balance || 0) : 0,
    usedConfigs: user ? (user.used_configs || []) : []
  };
};