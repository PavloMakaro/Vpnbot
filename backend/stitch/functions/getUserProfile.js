exports = async function(arg){
  const user_id = context.user.id;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");

  const user = await db.collection("users").findOne({ _id: user_id });
  if (!user) {
    throw new Error("User not found");
  }

  return {
    _id: user._id,
    username: user.username,
    first_name: user.first_name,
    balance: user.balance,
    subscription_end: user.subscription_end,
    referrals_count: user.referrals_count
  };
};
