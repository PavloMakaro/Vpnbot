exports = async function(loginPayload) {
  const crypto = require("crypto");

  // The loginPayload from Custom Function Authentication contains the payload sent by the client.
  // We expect loginPayload.initData to contain the Telegram initData string.
  const initData = loginPayload.initData;
  if (!initData) {
    throw new Error("Missing initData in login payload");
  }

  // Parse initData to extract user info and hash
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get("hash");
  if (!hash) {
    throw new Error("Missing hash in initData");
  }

  // Remove hash to create the data-check-string
  urlParams.delete("hash");

  // Sort the remaining keys alphabetically
  const keys = Array.from(urlParams.keys()).sort();
  const dataCheckString = keys.map(key => `${key}=${urlParams.get(key)}`).join('\n');

  // Verify HMAC-SHA-256
  // Get bot token from Context Values
  const botToken = context.values.get("BOT_TOKEN");
  if (!botToken) {
    throw new Error("BOT_TOKEN is not configured in Context Values");
  }

  const secretKey = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData signature");
  }

  // Parse the user string from initData to get user details
  const userStr = urlParams.get("user");
  if (!userStr) {
    throw new Error("Missing user data in initData");
  }

  const user = JSON.parse(userStr);
  const telegramId = user.id.toString();
  const username = user.username || "";
  const firstName = user.first_name || "";

  // Connect to MongoDB Atlas
  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  // Upsert user profile
  const updateResult = await usersCollection.updateOne(
    { _id: telegramId },
    {
      $set: {
        username: username,
        first_name: firstName,
        last_login: new Date()
      },
      $setOnInsert: {
        balance: 50, // Initial referral bonus from legacy code
        subscription_end: null,
        referrals_count: 0,
        used_configs: []
      }
    },
    { upsert: true }
  );

  // Return the ID that Atlas App Services will use to map this user.
  // This must be a string representing a unique ID.
  return telegramId;
};
