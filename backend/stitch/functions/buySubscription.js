exports = async function(period) {
  const userId = context.user.id;

  const periods = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  if (!periods[period]) {
    throw new Error("Invalid subscription period");
  }

  const { price, days } = periods[period];

  const cluster = context.services.get("mongodb-atlas");
  const usersCollection = cluster.db("vpn_bot").collection("users");
  const configsCollection = cluster.db("vpn_bot").collection("configs");

  // Get user profile
  const user = await usersCollection.findOne({ _id: userId });
  if (!user) throw new Error("User not found");
  if (user.balance < price) throw new Error("Insufficient balance");

  // Atomically reserve a config
  const config = await configsCollection.findOneAndUpdate(
    { period: period, used: false },
    { $set: { used: true } },
    { returnNewDocument: true }
  );

  if (!config) {
    throw new Error("No available configs for this period");
  }

  // Calculate new subscription end date
  let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
  if (currentEnd < new Date()) {
    currentEnd = new Date();
  }
  const newEnd = new Date(currentEnd.getTime() + days * 24 * 60 * 60 * 1000);

  // Format dates for saving in user record
  const issueDateStr = new Date().toISOString().replace('T', ' ').substring(0, 19);
  const newEndStr = newEnd.toISOString().replace('T', ' ').substring(0, 19);

  // Update user balance and subscription, and add to used_configs
  const updatedUser = await usersCollection.findOneAndUpdate(
    { _id: userId },
    {
      $inc: { balance: -price },
      $set: { subscription_end: newEndStr },
      $push: {
        used_configs: {
          config_name: config.name,
          config_link: config.link,
          config_code: config.code,
          period: period,
          issue_date: issueDateStr,
          user_name: `${user.first_name} (@${user.username})`
        }
      }
    },
    { returnNewDocument: true }
  );

  return {
    success: true,
    config: config,
    newBalance: updatedUser.balance,
    subscriptionEnd: updatedUser.subscription_end
  };
};
