exports = async function() {
  const user = context.user;

  if (!user || !user.id) {
    throw new Error("Authentication required.");
  }

  const mongodb = context.services.get("mongodb-atlas");
  const db = mongodb.db("vpn_bot");
  const configsCollection = db.collection("configs");

  // Hardcoded from legacy Python bot
  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const results = {};

  for (const [period, details] of Object.entries(SUBSCRIPTION_PERIODS)) {
    // Count available configs for this period
    const availableCount = await configsCollection.count({ period: period, used: false });

    results[period] = {
      ...details,
      available_configs: availableCount
    };
  }

  return results;
};
