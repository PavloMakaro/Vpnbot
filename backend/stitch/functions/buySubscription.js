exports = async function(period) {
  // Config: Prices
  const prices = {
    '1_month': 50,
    '2_months': 90,
    '3_months': 120
  };

  if (!prices[period]) {
    throw new Error("Invalid period");
  }

  const price = prices[period];

  const user = context.user;
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  // Start Transaction (if supported by Atlas config/tier, else simple updates)
  // For simplicity, we'll do sequential checks.

  const userDoc = await usersCollection.findOne({ telegram_id: user.id });

  if (!userDoc || userDoc.balance < price) {
    throw new Error("Insufficient balance");
  }

  // Find available config
  const availableConfig = await configsCollection.findOneAndUpdate(
    { period: period, used: false },
    { $set: { used: true, used_by: user.id, date_assigned: new Date() } },
    { returnNewDocument: true }
  );

  if (!availableConfig) {
    throw new Error("No configs available for this period. Please contact support.");
  }

  // Calculate new subscription end date
  let currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : new Date();
  if (currentEnd < new Date()) {
    currentEnd = new Date();
  }

  // Add days based on period (assuming period key contains '_month')
  let months = parseInt(period.split('_')[0]);
  if (isNaN(months)) months = 1;

  currentEnd.setMonth(currentEnd.getMonth() + months);

  // Update user
  await usersCollection.updateOne(
    { telegram_id: user.id },
    {
      $inc: { balance: -price },
      $set: { subscription_end: currentEnd },
      $push: {
        configs: {
          name: availableConfig.name || "VPN Config",
          link: availableConfig.link,
          period: period,
          date: new Date()
        }
      }
    }
  );

  return { success: true, new_balance: userDoc.balance - price, subscription_end: currentEnd, config: availableConfig.link };
};
