exports = async function(arg){
  const user = context.user;
  const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const userProfile = await users.findOne({ _id: user.id });

  if (!userProfile) {
    throw new Error("User not found");
  }

  return userProfile.used_configs || [];
};
