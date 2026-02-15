exports = async function() {
  const userId = context.user.id;
  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  const configs = await configsCollection.find({ used_by: userId.toString() }).toArray();

  return configs.map(c => ({
    name: c.name || "VPN Config",
    period: c.period,
    link: c.link,
    used_at: c.used_at
  }));
};
