exports = async function() {
  const userId = context.user.id;
  const configs = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  // Find all configs assigned to this user
  const myConfigs = await configs.find({ assigned_to: userId }).toArray();

  return myConfigs;
};
