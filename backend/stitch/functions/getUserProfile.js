exports = async function() {
  const userId = context.user.id;
  const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const user = await users.findOne({ _id: userId });
  if (!user) {
    // Should generally be handled by login function, but safe fallback
    return null;
  }

  return {
    _id: user._id,
    balance: user.balance,
    subscription_end: user.subscription_end,
    referrals_count: user.referrals_count,
    username: user.username,
    first_name: user.first_name
  };
};
