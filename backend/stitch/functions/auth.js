exports = async function(loginPayload) {
  const crypto = require('crypto');
  const botToken = context.values.get("BOT_TOKEN");

  if (!botToken) {
    throw new Error("BOT_TOKEN value not found");
  }

  const { initData } = loginPayload;
  if (!initData) {
    throw new Error("No initData provided");
  }

  // Parse initData
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');

  // Sort keys alphabetically
  const dataCheckString = Array.from(urlParams.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, val]) => `${key}=${val}`)
    .join('\n');

  // Validate hash
  const secretKey = crypto.createHmac('sha256', "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid hash");
  }

  // Parse user data
  const userDataStr = urlParams.get('user');
  if (!userDataStr) {
      throw new Error("No user data found in initData");
  }
  const userData = JSON.parse(userDataStr);
  const userId = userData.id.toString();

  // Upsert user into database
  const mongodb = context.services.get("mongodb-atlas");
  const users = mongodb.db("vpn_bot").collection("users");

  await users.updateOne(
    { _id: userId },
    {
      $setOnInsert: {
        balance: 50, // Initial bonus from old bot logic
        subscription_end: null,
        referrals_count: 0,
        joined_at: new Date()
      },
      $set: {
        username: userData.username,
        first_name: userData.first_name,
        last_login: new Date()
      }
    },
    { upsert: true }
  );

  // Return the user ID as the identity for Custom Function Auth
  return userId;
};
