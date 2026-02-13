exports = async function(){
  const user = context.user;
  if (!user) {
    throw new Error("User not authenticated");
  }

  const userId = user.id;
  const collection = context.services.get("mongodb-atlas").db("vpn_bot_db").collection("users");

  const doc = await collection.findOne({ _id: userId }, { projection: { used_configs: 1 } });

  return doc ? (doc.used_configs || []) : [];
};
