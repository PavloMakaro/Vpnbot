exports = async function() {
  const user = context.user;
  if (!user) throw new Error("Unauthorized");

  const identity = user.identities.find(id => id.provider_type === 'custom-function');
  const telegramId = identity ? identity.id : user.id;

  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const doc = await usersCollection.findOne(
    { _id: telegramId },
    { projection: { used_configs: 1 } }
  );

  return doc ? (doc.used_configs || []) : [];
};
