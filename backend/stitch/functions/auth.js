exports = async function(loginPayload) {
  // Extract initData from the login payload
  const { initData } = loginPayload;

  if (!initData) {
    throw new Error("Missing initData");
  }

  // Parse initData
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');

  // Sort parameters alphabetically
  const sortedParams = Array.from(urlParams.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  const dataCheckString = sortedParams.map(([key, value]) => `${key}=${value}`).join('\n');

  // Validate the hash using HMAC-SHA-256
  // Note: There is NO development bypass here as per instructions.
  const botToken = context.values.get("BOT_TOKEN");
  if (!botToken) {
    throw new Error("BOT_TOKEN Context Value is not set");
  }

  const crypto = require("crypto");
  const secretKey = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData hash");
  }

  // Authentication successful. Parse user info.
  const userJson = urlParams.get('user');
  if (!userJson) {
     throw new Error("No user info in initData");
  }

  const user = JSON.parse(userJson);
  const telegramId = user.id.toString();

  // Upsert user profile in MongoDB
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const existingUser = await usersCollection.findOne({ _id: telegramId });

  const updateDoc = {
    $set: {
      username: user.username || "N/A",
      first_name: user.first_name || "N/A"
    }
  };

  // If new user, give a starting balance
  if (!existingUser) {
    updateDoc.$setOnInsert = {
      balance: 50, // Initial referral/welcome bonus
      subscription_end: null,
      used_configs: [],
      referrals_count: 0
    };
  }

  await usersCollection.updateOne(
    { _id: telegramId },
    updateDoc,
    { upsert: true }
  );

  // Return the custom ID so Atlas links the session correctly
  return telegramId;
};
