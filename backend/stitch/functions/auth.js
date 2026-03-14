exports = async function(loginPayload) {
  // Validate Telegram Web App initData
  const crypto = require('crypto');
  const BOT_TOKEN = context.values.get("BOT_TOKEN");

  if (!BOT_TOKEN) {
    console.error("BOT_TOKEN is not configured.");
    throw new Error("Internal Server Error: Missing bot configuration.");
  }

  const initData = loginPayload.initData;
  if (!initData) {
     throw new Error("Missing initData");
  }

  // Parse initData
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');

  const dataCheckString = Array.from(urlParams.entries())
    .map(([key, value]) => `${key}=${value}`)
    .sort()
    .join('\n');

  const secretKey = crypto.createHmac('sha256', 'WebAppData')
    .update(BOT_TOKEN)
    .digest();

  const calculatedHash = crypto.createHmac('sha256', secretKey)
    .update(dataCheckString)
    .digest('hex');

  if (calculatedHash !== hash) {
    console.error("Invalid Telegram initData hash.");
    throw new Error("Authentication failed: Invalid hash");
  }

  // Authentication successful, extract user info
  const userStr = urlParams.get('user');
  if (!userStr) {
    throw new Error("Authentication failed: Missing user data");
  }

  const userObj = JSON.parse(userStr);
  const userIdStr = userObj.id.toString();

  // Upsert user into MongoDB
  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  await usersCollection.updateOne(
    { telegram_id: userObj.id },
    {
      $set: {
        telegram_id: userObj.id,
        username: userObj.username || "N/A",
        first_name: userObj.first_name || "N/A"
      },
      $setOnInsert: {
         balance: 50, // Initial balance
         subscription_end: null,
         referrals_count: 0,
         used_configs: []
      }
    },
    { upsert: true }
  );

  // Return the custom identity which Atlas uses as the User ID
  return userIdStr;
};
