exports = async function() {
  const user = context.user;
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const userDoc = await usersCollection.findOne({ _id: user.id });

  if (!userDoc || !userDoc.used_configs) {
    return [];
  }

  return userDoc.used_configs;
};
