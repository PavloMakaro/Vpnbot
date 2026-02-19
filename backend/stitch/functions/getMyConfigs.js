exports = async function() {
  const mongodb = context.services.get("mongodb-atlas");
  const configs = mongodb.db("vpn_bot").collection("configs");

  // Query for configs assigned to the current user
  // Assuming assigned_to stores the user ID as string
  const cursor = configs.find({ assigned_to: context.user.id });

  return await cursor.toArray();
};
