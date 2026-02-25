exports = async function(initData) {
  // Authentication function for Telegram Mini App
  // Validates initData and upserts user

  const crypto = require('crypto');
  const secret = context.values.get("BOT_TOKEN"); // Token should be stored in App Services Values

  if (!secret) {
    throw new Error("BOT_TOKEN not found in context values");
  }

  // Parse initData
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get("hash");
  urlParams.delete("hash");

  // Sort keys
  const dataCheckString = Array.from(urlParams.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");

  // Validate hash
  const secretKey = crypto.createHmac('sha256', "WebAppData").update(secret).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData hash");
  }

  // Parse user data
  const userStr = urlParams.get("user");
  if (!userStr) {
    throw new Error("User data missing in initData");
  }
  const telegramUser = JSON.parse(userStr);

  // Upsert user in MongoDB
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const updateResult = await collection.updateOne(
    { _id: telegramUser.id.toString() },
    {
      $set: {
        username: telegramUser.username,
        first_name: telegramUser.first_name,
        last_auth: new Date()
      },
      $setOnInsert: {
        balance: 0,
        subscription_end: null,
        referrals_count: 0,
        used_configs: []
      }
    },
    { upsert: true }
  );

  return { id: telegramUser.id.toString(), username: telegramUser.username };
};
