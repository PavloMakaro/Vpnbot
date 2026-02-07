exports = async function() {
  const userId = context.user.id;
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const user = await collection.findOne({ user_id: userId });

  if (!user || !user.used_configs) {
    return [];
  }

  return user.used_configs.sort((a, b) => new Date(b.issue_date) - new Date(a.issue_date));
};
