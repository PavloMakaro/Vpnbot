exports = async function() {
  // Returns the list of configs assigned to the authenticated user.

  const user = context.user;
  const userId = user.id;

  const collection = context.services.get("mongodb-atlas").db("vpn_bot_db").collection("configs");

  // Find all configs assigned to this user, sorted by assignment date (descending)
  const configs = await collection.find(
    { assigned_to: userId }
  ).sort({ assigned_at: -1 }).toArray();

  return configs;
};
