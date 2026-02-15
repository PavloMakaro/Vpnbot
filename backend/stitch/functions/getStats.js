exports = async function() {
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");
  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");

  const totalUsers = await usersCollection.count({});
  const activeSubs = await usersCollection.count({ subscription_end: { $gt: new Date() } });

  const totalConfigs = await configsCollection.count({});
  const usedConfigs = await configsCollection.count({ used: true });

  // Aggregate revenue
  const revenuePipeline = [
    { $match: { status: "succeeded" } },
    { $group: { _id: null, total: { $sum: "$amount" } } }
  ];
  const revenueResult = await paymentsCollection.aggregate(revenuePipeline).toArray();
  const totalRevenue = revenueResult.length > 0 ? revenueResult[0].total : 0;

  return {
    total_users: totalUsers,
    active_subscriptions: activeSubs,
    configs_total: totalConfigs,
    configs_used: usedConfigs,
    configs_available: totalConfigs - usedConfigs,
    total_revenue: totalRevenue
  };
};
