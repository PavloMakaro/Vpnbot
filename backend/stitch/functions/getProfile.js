exports = async function() {
  const telegramId = context.user.identities[0].id;

  if (!telegramId) {
    throw new Error("No Telegram ID found in context");
  }

  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const profile = await usersCollection.findOne({ _id: telegramId });

  if (!profile) {
    throw new Error("Profile not found");
  }

  return profile;
};
