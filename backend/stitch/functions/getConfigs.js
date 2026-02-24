exports = async function() {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("Unauthorized");
  }

  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const userDoc = await collection.findOne({ _id: user.id });

  if (!userDoc || !userDoc.used_configs) {
    return [];
  }

  return userDoc.used_configs;
};
