exports = async function() {
  const currentUser = context.user;
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const user = await usersCollection.findOne({ _id: currentUser.id });

  if (!user) {
    throw new Error("User not found");
  }

  return {
    _id: user._id,
    username: user.username,
    first_name: user.first_name,
    balance: user.balance,
    subscription_end: user.subscription_end,
    referrals_count: user.referrals_count,
    used_configs: user.used_configs || []
  };
};