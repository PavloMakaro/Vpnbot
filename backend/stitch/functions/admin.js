exports = async function(action, payload) {
  // Admin functions for managing configs and users.
  // action: "add_configs", "get_stats"
  // payload: object with arguments for the action

  const user = context.user;
  const adminId = context.values.get("adminUserId"); // Configure this in Stitch Values

  if (user.id !== adminId) {
    throw new Error("Unauthorized: You are not an admin.");
  }

  const client = context.services.get("mongodb-atlas");
  const db = client.db("vpn_bot_db");
  const configsCollection = db.collection("configs");
  const usersCollection = db.collection("users");
  const paymentsCollection = db.collection("payments");

  if (action === "add_configs") {
    // payload: { period: "1_month", links: ["link1", "link2"] }
    const period = payload.period;
    const links = payload.links;

    if (!period || !links || !Array.isArray(links)) {
      throw new Error("Invalid payload for add_configs");
    }

    const docs = links.map((link, index) => ({
      period: period,
      link: link,
      name: `Config_${period}_${new Date().getTime()}_${index}`,
      code: `code_${period}_${new Date().getTime()}_${index}`,
      used: false,
      created_at: new Date()
    }));

    if (docs.length > 0) {
      const result = await configsCollection.insertMany(docs);
      const insertedCount = Object.keys(result.insertedIds).length;
      return {
        success: true,
        message: `Added ${insertedCount} configs for ${period}`,
        inserted_ids: result.insertedIds
      };
    } else {
      return { success: false, message: "No configs to add" };
    }
  }

  else if (action === "get_stats") {
    const totalUsers = await usersCollection.count({});
    const totalRevenueResult = await paymentsCollection.aggregate([
      { $match: { status: "succeeded" } },
      { $group: { _id: null, total: { $sum: "$amount" } } }
    ]).toArray();

    const totalRevenue = totalRevenueResult.length > 0 ? totalRevenueResult[0].total : 0;

    // Config counts
    const configStats = await configsCollection.aggregate([
       { $group: { _id: { period: "$period", used: "$used" }, count: { $sum: 1 } } }
    ]).toArray();

    return {
      success: true,
      stats: {
        total_users: totalUsers,
        total_revenue: totalRevenue,
        config_stats: configStats
      }
    };
  }

  throw new Error(`Unknown action: ${action}`);
};
