exports = async function() {
  const tgId = context.user.identities[0].id;
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const user = await usersCollection.findOne({ _id: tgId });
  if (!user) {
    throw new Error("User not found");
  }

  return {
    balance: user.balance || 0,
    subscription_end: user.subscription_end || null,
    used_configs: user.used_configs || []
  };
};