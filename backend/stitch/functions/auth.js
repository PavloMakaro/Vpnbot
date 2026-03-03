exports = async function(loginPayload) {
  // Validate telegram initData via HMAC-SHA-256
  const crypto = require("crypto");
  const initData = loginPayload.initData;
  const botToken = context.values.get("BOT_TOKEN");

  if (!initData || !botToken) {
    throw new Error("Missing initData or BOT_TOKEN");
  }

  // Parse initData string
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');

  // Sort params alphabetically
  const params = [];
  for (const [key, value] of urlParams.entries()) {
    params.push(`${key}=${value}`);
  }
  params.sort();

  const dataCheckString = params.join('\n');

  // Compute HMAC
  const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData hash");
  }

  // Extract user info
  const userStr = urlParams.get('user');
  if (!userStr) {
     throw new Error("Missing user object in initData");
  }
  const tgUser = JSON.parse(decodeURIComponent(userStr));

  // Upsert user into users collection
  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn").collection("users");

  const userId = tgUser.id.toString();

  const existingUser = await usersCollection.findOne({ _id: userId });

  if (!existingUser) {
    // New user
    const newUser = {
      _id: userId,
      username: tgUser.username || "N/A",
      first_name: tgUser.first_name || "N/A",
      balance: 50, // Welcome bonus
      subscription_end: null,
      referrals_count: 0,
      used_configs: [],
      created_at: new Date()
    };
    await usersCollection.insertOne(newUser);
  } else {
    // Update user profile info
    await usersCollection.updateOne(
      { _id: userId },
      {
        $set: {
          username: tgUser.username || "N/A",
          first_name: tgUser.first_name || "N/A",
          last_login: new Date()
        }
      }
    );
  }

  // Return the user ID to be used as the Realm User ID
  return userId;
};
