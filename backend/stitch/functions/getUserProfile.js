exports = async function() {
  // Get current user context
  const user = context.user;
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Find user by ID
  let userDoc = await usersCollection.findOne({ _id: user.id });

  if (!userDoc) {
    // If user not found, create new
    // user.data contains the return value of auth function
    const userData = user.data || {};

    userDoc = {
      _id: user.id,
      username: userData.username || "",
      first_name: userData.first_name || "",
      balance: 50, // Welcome bonus (as per ai_studio_code.py: REFERRAL_BONUS_NEW_USER)
      referrals_count: 0,
      subscription_end: null,
      created_at: new Date(),
      used_configs: []
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
    ...userDoc,
    days_left: daysLeft
  };
};
