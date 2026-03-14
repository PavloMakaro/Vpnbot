exports = async function() {
  const user = context.user;
  if (!user || !user.identities || user.identities.length === 0) {
      throw new Error("User not authenticated properly.");
  }

  // Extract custom identity ID which is the Telegram ID
  const telegramId = user.identities[0].id;

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  // Since user.id from context is a string, and telegram_id might be stored as a number, we should check both or convert.
  let parsedId = parseInt(telegramId);
  if (isNaN(parsedId)) {
      parsedId = telegramId; // fallback
  }

  const profile = await usersCollection.findOne({ telegram_id: parsedId });

  if (!profile) {
      // If not found as integer, try string
      const profileStr = await usersCollection.findOne({ telegram_id: telegramId });
      if (!profileStr) {
        throw new Error("Profile not found");
      }
      return profileStr;
  }
  return profile;
};
