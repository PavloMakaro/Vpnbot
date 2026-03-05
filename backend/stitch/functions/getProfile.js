exports = async function() {
  const user = context.user;
  if (!user || !user.custom_data) {
    throw new Error("Authentication failed: User custom data is missing.");
  }

  // Get current user ID
  const userId = user.custom_data._id || user.id;

  // Connect to DB
  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  const profile = await usersCollection.findOne({ _id: userId });

  if (!profile) {
      throw new Error("Profile not found.");
  }

  // Clean up sensitive fields before returning
  delete profile._id;
  delete profile.created_at;
  delete profile.last_login;

  // Format days left
  let days_left = 0;
  if (profile.subscription_end) {
      const now = new Date();
      let subEnd;
      if (profile.subscription_end instanceof Date) {
          subEnd = profile.subscription_end;
      } else {
          subEnd = new Date(profile.subscription_end);
      }

      if (subEnd > now) {
          days_left = Math.floor((subEnd.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
      }
  }

  return {
    ...profile,
    days_left: days_left,
    subscription_end: profile.subscription_end ? new Date(profile.subscription_end).toLocaleString() : null
  };
};