exports = async function(loginPayload) {
  const crypto = require("crypto");
  const initData = loginPayload.initData;
  const botToken = context.values.get("BOT_TOKEN");

  if (!initData || !botToken) {
    throw new Error("Missing initData or BOT_TOKEN");
  }

  // Parse initData
  const params = new URLSearchParams(initData);
  const hash = params.get("hash");
  params.delete("hash");

  // Sort parameters alphabetically
  const dataCheckString = Array.from(params.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");

  // Generate secret key
  const secretKey = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();

  // Calculate signature
  const calculatedHash = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData signature");
  }

  // Parse user data
  const userStr = params.get("user");
  if (!userStr) {
    throw new Error("Missing user data in initData");
  }

  const userData = JSON.parse(decodeURIComponent(userStr));
  const telegramId = userData.id.toString();
  const username = userData.username || "N/A";
  const firstName = userData.first_name || "N/A";

  // Upsert user profile into database
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");

  await usersCollection.updateOne(
    { telegram_id: telegramId },
    {
      $setOnInsert: {
        balance: 0,
        subscription_end: null,
        referrals_count: 0,
        used_configs: []
      },
      $set: {
        username: username,
        first_name: firstName,
        last_login: new Date()
      }
    },
    { upsert: true }
  );

  return telegramId;
};
