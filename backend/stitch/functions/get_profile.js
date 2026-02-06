exports = async function() {
  // Get the current user
  const user = context.user;
  const userId = user.id; // This is the Telegram ID (string) returned by auth function

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  // Find or create user
  let userDoc = await usersCollection.findOne({ _id: userId });

  if (!userDoc) {
    // New user
    userDoc = {
      _id: userId,
      balance: 0,
      subscription_end: null,
      first_name: user.data.name || "User",
      username: "", // We might want to update this from initData if possible, or leave empty
      referrals_count: 0,
      used_configs: [],
      created_at: new Date()
    };
    await usersCollection.insertOne(userDoc);
  }

  // Calculate days left
  let daysLeft = 0;
  if (userDoc.subscription_end) {
    const end = new Date(userDoc.subscription_end);
    const now = new Date();
    if (end > now) {
      const diffTime = Math.abs(end - now);
      daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }
  }

  return {
    user_id: userId,
    first_name: userDoc.first_name,
    balance: userDoc.balance,
    subscription_end: userDoc.subscription_end,
    days_left: daysLeft
  };
};
