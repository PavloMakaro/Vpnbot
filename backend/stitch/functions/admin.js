exports = async function(action, payload){
  const user = context.user;
  if (!user) {
    throw new Error("User not authenticated");
  }

  const ADMIN_ID = "8320218178";
  if (user.id !== ADMIN_ID) {
    throw new Error("Unauthorized");
  }

  const db = context.services.get("mongodb-atlas").db("vpn_bot_db");
  const configsCollection = db.collection("configs");
  const usersCollection = db.collection("users");
  const paymentsCollection = db.collection("payments");

  if (action === "add_configs") {
    const { period, links } = payload; // links is array of strings
    if (!links || !Array.isArray(links)) {
      throw new Error("Invalid links");
    }

    const docs = links.map((link, index) => ({
      period: period,
      link: link,
      code: `code_${period}_${new Date().getTime()}_${index}`,
      name: `Config_${period}_${new Date().getTime()}_${index}`,
      used: false,
      created_at: new Date()
    }));

    if (docs.length > 0) {
      await configsCollection.insertMany(docs);
    }
    return { success: true, count: docs.length };

  } else if (action === "get_stats") {
    const totalUsers = await usersCollection.count({});
    const totalPayments = await paymentsCollection.count({});

    // Aggregation for revenue
    const revenuePipe = [
      { $match: { status: 'confirmed' } },
      { $group: { _id: null, total: { $sum: "$amount" } } }
    ];
    const revenueRes = await paymentsCollection.aggregate(revenuePipe).toArray();
    const revenue = revenueRes.length > 0 ? revenueRes[0].total : 0;

    // Config stats
    const configStatsPipe = [
      { $group: { _id: { period: "$period", used: "$used" }, count: { $sum: 1 } } }
    ];
    const configStats = await configsCollection.aggregate(configStatsPipe).toArray();

    return {
      total_users: totalUsers,
      total_payments: totalPayments,
      revenue: revenue,
      config_stats: configStats
    };
  }

  throw new Error("Unknown action");
};
