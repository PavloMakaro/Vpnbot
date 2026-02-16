exports = async function() {
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Use Authenticated User ID
  const userId = context.user.id;

  if (!userId) {
    return { error: "Not authenticated" };
  }

  const user = await usersCollection.findOne({ _id: userId });

  if (!user) {
    return { error: "User not found" };
  }

  return { user: user };
};
