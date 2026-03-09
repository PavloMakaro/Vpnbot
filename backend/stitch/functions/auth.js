exports = async function(loginPayload) {
  // Extract and parse telegram initData.
  const initDataStr = loginPayload.initData;
  if (!initDataStr) {
    throw new Error("Missing initData");
  }

  // Parse initData into an object
  const urlParams = new URLSearchParams(initDataStr);
  const dataMap = new Map();
  for (const [key, value] of urlParams.entries()) {
      dataMap.set(key, value);
  }

  // In production, you would validate the initData against BOT_TOKEN using HMAC-SHA-256 here.
  // We skip it in this generic example, but in a real Stitch Custom Auth function:
  // const crypto = require('crypto');
  // const botToken = context.values.get("BOT_TOKEN");
  // const hash = crypto.createHmac('sha256', "WebAppData").update(botToken).digest();
  // ... and verify `hash` matches dataMap.get("hash")

  // For local testing & this mock setup, we assume valid initData

  const userJson = dataMap.get("user");
  if (!userJson) {
      throw new Error("Missing user data in initData");
  }

  const userData = JSON.parse(userJson);
  const telegramId = userData.id.toString();

  // Upsert user into MongoDB
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const updateResult = await collection.findOneAndUpdate(
    { _id: telegramId },
    {
      $setOnInsert: {
         _id: telegramId,
         balance: 50, // Initial bonus
         subscription_end: null,
         referrals_count: 0,
         used_configs: [],
         created_at: new Date()
      },
      $set: {
         username: userData.username || "N/A",
         first_name: userData.first_name || "N/A",
         last_login: new Date()
      }
    },
    { upsert: true, returnNewDocument: true }
  );

  // Return the identity string which Realm uses to link the user
  return telegramId;
};