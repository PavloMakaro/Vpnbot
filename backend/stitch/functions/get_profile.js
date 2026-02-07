exports = async function() {
  // Get the current authenticated user's ID
  const userId = context.user.id; // This is the Stitch User ID (string)
  // We need to map it to the Telegram User ID.
  // In our custom auth function, we returned the Telegram ID as the Stitch User ID (or close to it).
  // Assuming the custom auth provider uses the returned ID as the user identity.

  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Find user in DB
  const userDoc = await collection.findOne({ user_id: userId });

  if (!userDoc) {
    // If user doesn't exist, create a new one (first login via Mini App)
    const newUser = {
      user_id: userId,
      balance: 0,
      subscription_end: null,
      username: context.user.data.username || "", // Might need to pass this in profile update if not available
      first_name: context.user.data.first_name || "User",
      created_at: new Date()
    };
    await collection.insertOne(newUser);
    return newUser;
  }

  return userDoc;
};
