exports = async function() {
  // This function is called by the frontend to get the user's profile.
  // It handles user creation if they don't exist yet.

  const user = context.user;
  const userId = user.id;
  const userData = user.data; // Data from auth provider (name, username)

  const collection = context.services.get("mongodb-atlas").db("vpn_bot_db").collection("users");

  try {
    let userProfile = await collection.findOne({ _id: userId });

    if (!userProfile) {
      // Create new user profile
      userProfile = {
        _id: userId,
        first_name: userData.name || "User",
        username: userData.username || "",
        balance: 50, // Welcome bonus (same as Python bot)
        subscription_end: null,
        created_at: new Date(),
        used_configs: [],
        referrals_count: 0,
        referred_by: null // Logic for referral to be added if passed
      };

      await collection.insertOne(userProfile);
      console.log(`Created new user: ${userId}`);
    } else {
        // Update name/username if changed
        if (userProfile.first_name !== userData.name || userProfile.username !== userData.username) {
            await collection.updateOne(
                { _id: userId },
                { $set: { first_name: userData.name, username: userData.username } }
            );
        }
    }

    return userProfile;
  } catch (err) {
    console.error("Error in getUserProfile:", err);
    throw err;
  }
};
