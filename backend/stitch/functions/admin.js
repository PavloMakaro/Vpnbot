exports = async function(action, payload) {
  const user_id = context.user.id;
  const admin_id = context.values.get("adminId");

  if (!admin_id) {
    throw new Error("Admin ID not configured in App Services Values.");
  }

  if (user_id !== admin_id) {
    throw new Error("Unauthorized");
  }

  const db = context.services.get("mongodb-atlas").db("vpn_bot");

  switch (action) {
    case "add_config":
      // payload: { period: "1_month", configs: [{ link: "...", code: "..." }] }
      if (!payload.configs || !payload.period) throw new Error("Missing configs or period");

      const configs = payload.configs.map(c => ({
        period: payload.period,
        link: c.link,
        code: c.code || "",
        name: c.name || "Config",
        used: false,
        created_at: new Date()
      }));

      const result = await db.collection("configs").insertMany(configs);
      return { success: true, count: result.insertedIds.length };

    case "get_stats":
      const usersCount = await db.collection("users").count();
      const activeSubs = await db.collection("users").count({ subscription_end: { $gt: new Date() } });
      const configsCount = await db.collection("configs").count();
      const usedConfigsCount = await db.collection("configs").count({ used: true });

      return {
        users: usersCount,
        active_subscriptions: activeSubs,
        total_configs: configsCount,
        used_configs: usedConfigsCount
      };

    default:
      throw new Error("Unknown action: " + action);
  }
};
