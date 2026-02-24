exports = async function() {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("Unauthorized");
  }

  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Find user by _id (Telegram ID)
  const userDoc = await collection.findOne({ _id: user.id });

  if (!userDoc) {
    throw new Error("User not found");
  }

  return {
    _id: userDoc._id,
    username: userDoc.username,
    first_name: userDoc.first_name,
    balance: userDoc.balance || 0,
    subscription_end: userDoc.subscription_end,
    referrals_count: userDoc.referrals_count || 0,
    referred_by: userDoc.referred_by
  };
};
