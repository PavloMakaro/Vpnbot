exports = async function(arg){
  const user = context.user;
  if (!user) {
    throw new Error("User not authenticated");
  }

  const userId = user.id; // Or user.custom_data.user_id if using custom auth

  const collection = context.services.get("mongodb-atlas").db("vpn_bot_db").collection("users");

  // Find user by _id (Telegram ID)
  // Assuming the auth provider sets the user.id to the Telegram ID or we stored it
  // In the auth function I returned { id: user.id.toString() ... } so user.id might be that.
  // Actually, in Custom Function Auth, the returned ID becomes the user.id.

  const doc = await collection.findOne({ _id: userId });

  if (!doc) {
    return { error: "User not found" };
  }

  // Calculate subscription status
  let daysLeft = 0;
  if (doc.subscription_end) {
    const end = new Date(doc.subscription_end);
    const now = new Date();
    if (end > now) {
      const diff = end - now;
      daysLeft = Math.ceil(diff / (1000 * 60 * 60 * 24));
    }
  }

  return {
    username: doc.username,
    first_name: doc.first_name,
    balance: doc.balance,
    subscription_end: doc.subscription_end,
    days_left: daysLeft,
    referrals_count: doc.referrals_count || 0
  };
};
