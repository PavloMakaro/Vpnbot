exports = async function() {
  // Get the current user from context (populated by auth function)
  const user = context.user;
  if (!user) {
    throw new Error("User not authenticated");
  }

  const telegramId = user.id; // The custom auth function returns { id: telegramId }

  const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const userData = await users.findOne({ _id: telegramId });

  if (!userData) {
    throw new Error("User profile not found");
  }

  // Calculate days left
  let daysLeft = 0;
  if (userData.subscription_end) {
    const end = new Date(userData.subscription_end);
    const now = new Date();
    if (end > now) {
      const diffTime = Math.abs(end - now);
      daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }
  }

  return {
    ...userData,
    days_left: daysLeft
  };
};
