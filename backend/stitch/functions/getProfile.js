exports = async function() {
  const telegramId = context.user.identities[0].id;

  if (!telegramId) {
    throw new Error("User not authenticated");
  }

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");

  const user = await usersCollection.findOne({ telegram_id: telegramId });

  if (!user) {
    throw new Error("User profile not found");
  }

  return user;
};
