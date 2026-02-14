exports = async function() {
  const collection = context.services.get("mongodb-atlas").db("vpn_bot_db").collection("users");

  // Get current user from context
  const currentUser = context.user;
  if (!currentUser || !currentUser.id) {
    throw new Error("User not authenticated");
  }

  const telegramId = currentUser.id; // Or however the auth provider maps it

  // Upsert user to ensure they exist
  let user = await collection.findOne({ _id: telegramId });

  if (!user) {
    // Basic user creation
    user = {
      _id: telegramId,
      first_name: currentUser.data.first_name || "New User",
      username: currentUser.data.username || "",
      balance: 0, // Should be REFERRAL_BONUS_NEW_USER if new?
      subscription_end: null,
      referrals_count: 0,
      referred_by: null, // Logic for referral needs to be added
      created_at: new Date()
    };
    await collection.insertOne(user);

    // Check for referral logic if passed in context or separate call
  }

  // Calculate days left
  let days_left = 0;
  if (user.subscription_end) {
    const end = new Date(user.subscription_end);
    const now = new Date();
    if (end > now) {
      days_left = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
    }
  }

  return {
    ...user,
    days_left: days_left
  };
};
