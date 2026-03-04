exports = async function(loginPayload) {
  const crypto = require("crypto");

  // The loginPayload from the client will contain the parsed initData string
  // and potentially a parsed version of it.
  const { initData, user } = loginPayload;

  if (!initData) {
    throw new Error("Missing initData");
  }

  // Get the bot token from context values (store your bot token in App Services Values)
  const botToken = context.values.get("BOT_TOKEN");
  if (!botToken) {
    throw new Error("BOT_TOKEN is not configured on the server");
  }

  // Verify the initData
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');

  const dataCheckString = Array.from(urlParams.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');

  const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData hash");
  }

  // Parse user info if available in initData
  let tgUser;
  try {
    tgUser = JSON.parse(urlParams.get('user'));
  } catch (e) {
    throw new Error("Failed to parse user data from initData");
  }

  const tgUserId = String(tgUser.id);

  // Access the MongoDB collections
  const cluster = context.services.get("mongodb-atlas");
  const usersCollection = cluster.db("vpn_bot").collection("users");

  // Upsert the user profile
  const updateResult = await usersCollection.findOneAndUpdate(
    { _id: tgUserId },
    {
      $set: {
        username: tgUser.username || "N/A",
        first_name: tgUser.first_name || "N/A",
      },
      $setOnInsert: {
        balance: 50, // Initial balance/bonus
        subscription_end: null,
        used_configs: [],
        referrals_count: 0
      }
    },
    { upsert: true, returnNewDocument: true }
  );

  return tgUserId;
};
