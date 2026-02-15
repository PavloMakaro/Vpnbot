exports = async function(periodKey, configsText) {
  // Verify Admin
  const ADMIN_ID = context.values.get("ADMIN_ID"); // e.g. "12345678"

  // context.user.id contains the authenticated user ID (which we set to Telegram ID in auth function)
  if (!context.user || context.user.id !== ADMIN_ID) {
    throw new Error("Unauthorized");
  }

  const configsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  const links = configsText.split('\n').filter(line => line.trim() !== '');
  const docs = links.map((link, index) => ({
    period: periodKey,
    link: link.trim(),
    used: false,
    added_at: new Date(),
    name: `Config ${periodKey} #${index + 1}` // Simple naming strategy
  }));

  if (docs.length > 0) {
    await configsCollection.insertMany(docs);
  }

  return { added: docs.length };
};
