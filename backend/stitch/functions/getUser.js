exports = async function() {
  const user = context.user;
  if (!user) {
    throw new Error("User not authenticated");
  }

  // Find the Telegram ID from identities
  const telegramIdentity = user.identities.find(id => id.provider_type === 'custom-function');
  if (!telegramIdentity) {
    throw new Error("Telegram identity not found");
  }
  const telegramId = telegramIdentity.id;

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  const userProfile = await usersCollection.findOne({ _id: telegramId });

  if (!userProfile) {
    throw new Error("User profile not found");
  }

  return userProfile;
};
