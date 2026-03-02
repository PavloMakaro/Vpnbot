exports = async function(loginPayload) {
  // Validate the initData received from Telegram Web App
  // loginPayload should be the raw initData string.

  if (!loginPayload) {
    throw new Error("No initData provided.");
  }

  const crypto = require("crypto");

  // Replace this with your actual Bot Token from context values
  const botToken = context.values.get("BOT_TOKEN");
  if (!botToken) {
     console.error("BOT_TOKEN is not set in context values.");
     throw new Error("Internal Server Error: Missing Token");
  }

  // Parse initData
  // e.g. "query_id=xxx&user=%7B%22id%22%3A123...%7D&auth_date=123&hash=abc"
  const params = new URLSearchParams(loginPayload);

  const hash = params.get("hash");
  if (!hash) {
    throw new Error("Invalid initData: missing hash.");
  }

  params.delete("hash");

  // Sort parameters alphabetically
  const sortedParams = Array.from(params.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");

  // Compute secret key
  const secretKey = crypto
    .createHmac("sha256", "WebAppData")
    .update(botToken)
    .digest();

  // Compute data check
  const calculatedHash = crypto
    .createHmac("sha256", secretKey)
    .update(sortedParams)
    .digest("hex");

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData: signature mismatch.");
  }

  // Parse user object
  const userStr = params.get("user");
  if (!userStr) {
    throw new Error("Invalid initData: missing user.");
  }

  let userData;
  try {
    userData = JSON.parse(userStr);
  } catch (e) {
    throw new Error("Invalid initData: failed to parse user.");
  }

  const telegramId = userData.id.toString();
  const username = userData.username || null;
  const firstName = userData.first_name || null;
  const lastName = userData.last_name || null;

  // Connect to MongoDB
  const mongodb = context.services.get("mongodb-atlas");
  const db = mongodb.db("vpn_bot"); // replace with your DB name
  const usersCollection = db.collection("users");

  // Upsert user profile
  const result = await usersCollection.findOneAndUpdate(
    { _id: telegramId },
    {
      $set: {
        username: username,
        first_name: firstName,
        last_name: lastName,
        last_login: new Date()
      },
      $setOnInsert: {
        _id: telegramId,
        balance: 50, // Initial referral bonus from legacy code
        subscription_end: null,
        referrals_count: 0,
        used_configs: [],
        created_at: new Date()
      }
    },
    { returnNewDocument: true, upsert: true }
  );

  // Return the custom auth payload format that Realm expects for custom auth
  return telegramId;
};
