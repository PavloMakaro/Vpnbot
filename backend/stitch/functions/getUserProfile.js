exports = async function() {
  // In Custom Function Auth, the returned ID from auth.js becomes context.user.id
  const userId = context.user.id;

  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const user = await usersCollection.findOne({ _id: userId });

  if (!user) {
    throw new Error("User not found");
  }

  // Calculate days left
  let daysLeft = 0;
  if (user.subscription_end) {
    const end = new Date(user.subscription_end);
    const now = new Date();
    if (end > now) {
      daysLeft = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
    }
  }

  return {
    _id: user._id,
    username: user.username,
    first_name: user.first_name,
    balance: user.balance,
    subscription_end: user.subscription_end,
    days_left: daysLeft,
    referrals_count: user.referrals_count,
    used_configs: user.used_configs || []
  };
};
