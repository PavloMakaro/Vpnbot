exports = async function(loginPayload) {
  const crypto = require("crypto");

  // Extract token payload
  const initData = loginPayload.initData;
  if (!initData) {
    throw new Error("Missing initData payload");
  }

  // Extract BOT_TOKEN from context values
  const botToken = context.values.get("BOT_TOKEN");
  if (!botToken) {
    throw new Error("Missing BOT_TOKEN configuration in Atlas App Services");
  }

  // Parse initData string
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');

  // Sort keys and create data-check-string
  const paramsArray = Array.from(urlParams.entries());
  paramsArray.sort((a, b) => a[0].localeCompare(b[0]));
  const dataCheckString = paramsArray.map(p => `${p[0]}=${p[1]}`).join('\n');

  // Calculate HMAC-SHA-256 validation
  const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  // Check valid hash (NO BYPASSES PERMITTED)
  if (calculatedHash !== hash) {
    throw new Error("Invalid initData hash signature");
  }

  // Parse user JSON from initData
  let userObj;
  try {
    const userStr = urlParams.get('user');
    userObj = JSON.parse(userStr);
  } catch (err) {
    throw new Error("Could not parse user object from initData");
  }

  const telegramId = userObj.id.toString(); // Cast to string as specified in memory

  // Upsert user into MongoDB to maintain up-to-date username/first_name
  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  await usersCollection.updateOne(
    { telegram_id: telegramId },
    {
      $set: {
        username: userObj.username || "",
        first_name: userObj.first_name || "",
        last_login: new Date()
      },
      $setOnInsert: {
        telegram_id: telegramId,
        balance: 0,
        subscription_end: null,
        used_configs: [],
        referrals_count: 0
      }
    },
    { upsert: true }
  );

  return telegramId;
};
