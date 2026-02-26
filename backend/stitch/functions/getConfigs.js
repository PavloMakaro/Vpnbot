exports = async function() {
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const userId = context.user.id;

  const user = await collection.findOne({ _id: userId }, { projection: { used_configs: 1 } });

  if (!user) {
    throw new Error("User not found");
  }

  return user.used_configs || [];
};
