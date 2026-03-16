exports = async function(loginPayload) {
  const crypto = require("crypto");
  const initData = loginPayload.initData;

  // Extract variables
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');

  // Sort alphabetically
  const keys = Array.from(urlParams.keys()).sort();
  const dataCheckString = keys.map(key => `${key}=${urlParams.get(key)}`).join('\n');

  // Get bot token from environment variable context.values
  const botToken = context.values.get("BOT_TOKEN");
  if (!botToken) {
    throw new Error("BOT_TOKEN is missing");
  }

  const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData");
  }

  // Extract user info
  const userString = urlParams.get('user');
  if (!userString) {
    throw new Error("Missing user data");
  }

  const userObj = JSON.parse(userString);
  const tgId = userObj.id.toString();

  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Upsert user to users collection
  await usersCollection.updateOne(
    { _id: tgId },
    {
      $setOnInsert: {
        balance: 50, // Welcome bonus matching Python legacy
        referrals_count: 0,
        used_configs: []
      },
      $set: {
        username: userObj.username || 'N/A',
        first_name: userObj.first_name || 'N/A'
      }
    },
    { upsert: true }
  );

  return tgId;
};