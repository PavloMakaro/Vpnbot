exports = async function() {
  const user_id = context.user.id;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const users = db.collection("users");

  const user = await users.findOne({ _id: user_id });
  if (!user || !user.used_configs) {
    return [];
  }

  return user.used_configs;
};
