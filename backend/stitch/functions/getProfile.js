exports = async function(telegramId) {
  // Access the MongoDB service
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Find the user by their ID
  const user = await collection.findOne({ _id: telegramId });

  if (!user) {
    throw new Error("User not found");
  }

  // Calculate days left
  let days_left = 0;
  if (user.subscription_end) {
    const end_date = new Date(user.subscription_end);
    const now = new Date();
    if (end_date > now) {
      days_left = Math.max(0, Math.floor((end_date - now) / (1000 * 60 * 60 * 24)));
    }
  }

  // Format the response
  return {
    balance: user.balance || 0,
    subscription_end: user.subscription_end || null,
    days_left: days_left,
    first_name: user.first_name || "N/A",
    username: user.username || "N/A",
    referrals_count: user.referrals_count || 0,
    used_configs: user.used_configs || []
  };
};