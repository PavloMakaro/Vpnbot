exports = async function() {
  const user = context.user;

  if (!user || !user.id) {
    throw new Error("Authentication required.");
  }

  const mongodb = context.services.get("mongodb-atlas");
  const db = mongodb.db("vpn_bot");
  const usersCollection = db.collection("users");

  // Custom auth maps user id directly, but Realm custom data is preferred.
  // Using custom auth payload (Telegram ID)
  const telegramId = user.id;

  const profile = await usersCollection.findOne({ _id: telegramId });

  if (!profile) {
    throw new Error("User profile not found.");
  }

  // Calculate subscription days left
  let daysLeft = 0;
  if (profile.subscription_end) {
    const end = new Date(profile.subscription_end);
    const now = new Date();
    if (end > now) {
      const diffTime = Math.abs(end - now);
      daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }
  }

  return {
    id: profile._id,
    username: profile.username,
    first_name: profile.first_name,
    balance: profile.balance || 0,
    subscription_end: profile.subscription_end,
    days_left: daysLeft,
    used_configs: profile.used_configs || [],
    referrals_count: profile.referrals_count || 0
  };
};
