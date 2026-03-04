exports = async function() {
  const userId = context.user.id; // Returns the custom ID we mapped during auth

  const cluster = context.services.get("mongodb-atlas");
  const usersCollection = cluster.db("vpn_bot").collection("users");

  const userDoc = await usersCollection.findOne({ _id: userId });

  if (!userDoc) {
    throw new Error("User profile not found");
  }

  return {
    _id: userDoc._id,
    username: userDoc.username,
    first_name: userDoc.first_name,
    balance: userDoc.balance,
    subscription_end: userDoc.subscription_end,
    used_configs: userDoc.used_configs || []
  };
};
