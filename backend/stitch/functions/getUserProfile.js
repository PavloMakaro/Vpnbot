exports = async function(arg){
  const user = context.user;
  const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const userProfile = await users.findOne({ _id: user.id });

  if (!userProfile) {
    throw new Error("User not found");
  }

  return {
    _id: userProfile._id,
    username: userProfile.username,
    first_name: userProfile.first_name,
    balance: userProfile.balance,
    subscription_end: userProfile.subscription_end,
    referrals_count: userProfile.referrals_count,
    active_subscription: userProfile.subscription_end && new Date(userProfile.subscription_end) > new Date()
  };
};
