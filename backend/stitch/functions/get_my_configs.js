exports = async function() {
  const user = context.user;
  const userId = user.id;

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  const userDoc = await usersCollection.findOne({ _id: userId });

  if (!userDoc || !userDoc.used_configs) {
    return [];
  }

  return userDoc.used_configs;
};
