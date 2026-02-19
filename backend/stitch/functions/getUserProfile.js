exports = async function({ start_param, username, first_name }) {
  // Get database handle
  const mongodb = context.services.get("mongodb-atlas");
  const users = mongodb.db("vpn_bot").collection("users");

  // The authenticated user's ID (string)
  const userId = context.user.id;

  // Find existing user
  const user = await users.findOne({ _id: userId });

  if (user) {
    // Return existing profile
    return user;
  }

  // Define new user structure
  const newUser = {
    _id: userId,
    username: username || "N/A",
    first_name: first_name || "N/A",
    balance: 50, // Welcome bonus (REFERRAL_BONUS_NEW_USER)
    subscription_end: null,
    referrals_count: 0,
    referred_by: null,
    used_configs: [],
    created_at: new Date()
  };

  // Handle Referral Logic
  if (start_param && start_param !== userId) {
    // Check if referrer exists
    const referrer = await users.findOne({ _id: start_param });

    if (referrer) {
      newUser.referred_by = start_param;

      // Bonus logic for Referrer (REFERRAL_BONUS_REFERRER = 25, REFERRAL_BONUS_DAYS = 7)
      let currentEnd = referrer.subscription_end ? new Date(referrer.subscription_end) : new Date();
      if (currentEnd < new Date()) {
          currentEnd = new Date();
      }

      const newSubEnd = new Date(currentEnd.getTime() + (7 * 24 * 60 * 60 * 1000)); // Add 7 days

      await users.updateOne(
        { _id: start_param },
        {
          $inc: { balance: 25, referrals_count: 1 },
          $set: { subscription_end: newSubEnd }
        }
      );
    }
  }

  // Insert new user
  await users.insertOne(newUser);
  return newUser;
};
