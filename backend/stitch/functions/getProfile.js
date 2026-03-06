exports = async function() {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("User not authenticated");
  }

  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const profile = await collection.findOne({ _id: user.id });
  if (!profile) {
    throw new Error("User profile not found");
  }

  return {
    id: profile._id,
    username: profile.username,
    first_name: profile.first_name,
    balance: profile.balance || 0,
    subscription_end: profile.subscription_end,
    referrals_count: profile.referrals_count || 0,
    used_configs: profile.used_configs || []
  };
};