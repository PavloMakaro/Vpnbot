exports = async function() {
  const user = context.user;
  if (!user) throw new Error("Not authenticated");
  const telegramId = user.custom_data.telegram_id;

  const mongodb = context.services.get("mongodb-atlas");
  const users = mongodb.db("vpn_bot").collection("users");

  const userDoc = await users.findOne({ _id: telegramId });

  return userDoc ? (userDoc.used_configs || []) : [];
};
