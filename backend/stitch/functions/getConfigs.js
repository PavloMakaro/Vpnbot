exports = async function(arg) {
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const user = await collection.findOne({ _id: context.user.id });

  if (!user || !user.used_configs) {
    return [];
  }

  // Sort by issue date descending
  return user.used_configs.sort((a, b) => new Date(b.issue_date) - new Date(a.issue_date));
};
