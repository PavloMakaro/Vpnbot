exports = async function() {
  // Get current user profile
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("User not authenticated");
  }

  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const userProfile = await collection.findOne({ _id: user.id });

  if (!userProfile) {
    throw new Error("User profile not found");
  }

  // Calculate subscription days left
  let daysLeft = 0;
  if (userProfile.subscription_end) {
    const end = new Date(userProfile.subscription_end);
    const now = new Date();
    const diffTime = end - now;
    if (diffTime > 0) {
      daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }
  }

  return {
    ...userProfile,
    daysLeft: daysLeft
  };
};
