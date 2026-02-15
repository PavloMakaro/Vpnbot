exports = async function() {
  const userId = context.user.id;

  if (!userId) {
    throw new Error("Missing userId in context");
  }

  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const user = await usersCollection.findOne({ _id: userId.toString() });

  if (!user) {
    throw new Error("User not found");
  }

  const now = new Date();
  const subscriptionEnd = user.subscription_end ? new Date(user.subscription_end) : null;
  const isActive = subscriptionEnd && subscriptionEnd > now;

  // Calculate days left
  let daysLeft = 0;
  if (isActive) {
    const diffTime = Math.abs(subscriptionEnd - now);
    daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }

  return {
    _id: user._id,
    username: user.username,
    first_name: user.first_name,
    balance: user.balance || 0,
    subscription_end: user.subscription_end,
    subscription_active: isActive,
    days_left: daysLeft,
    referrals_count: user.referrals_count || 0,
    referral_link: `https://t.me/${context.values.get("BOT_USERNAME")}?start=${user._id}`
  };
};
