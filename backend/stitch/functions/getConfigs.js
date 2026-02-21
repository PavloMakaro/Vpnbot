exports = async function() {
  const user = context.user;
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const doc = await collection.findOne({ telegram_id: user.id });

  if (!doc) {
    return [];
  }

  return doc.configs || [];
};
