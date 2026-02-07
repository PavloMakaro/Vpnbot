exports = async function(loginPayload) {
  // Use standard crypto module available in Node.js runtime
  const crypto = require('crypto');

  // Get the initData string from the login payload
  const initData = loginPayload.initData;
  if (!initData) {
    throw new Error("No initData provided");
  }

  // Parse query string to object
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');

  // Sort keys alphabetically
  const dataCheckString = Array.from(urlParams.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');

  // Validate signature
  // SECURITY: Use a Value or Secret in App Services for the token
  // Example: const BOT_TOKEN = context.values.get("telegram_bot_token");
  const BOT_TOKEN = context.values.get("telegram_bot_token") || "YOUR_BOT_TOKEN_HERE";

  // Create secret key
  const secretKey = crypto.createHmac('sha256', "WebAppData")
    .update(BOT_TOKEN)
    .digest();

  // Calculate hash
  const calculatedHash = crypto.createHmac('sha256', secretKey)
    .update(dataCheckString)
    .digest('hex');

  // Verify signature
  if (calculatedHash !== hash) {
    throw new Error("Invalid signature");
  }

  // Parse user data
  const userData = JSON.parse(urlParams.get('user'));
  const userId = userData.id.toString();

  // Update user profile in DB
  // This ensures we always have fresh data from Telegram
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  await collection.updateOne(
    { user_id: userId },
    {
      $set: {
        first_name: userData.first_name,
        last_name: userData.last_name,
        username: userData.username,
        language_code: userData.language_code,
        last_login: new Date()
      },
      $setOnInsert: {
        balance: 0,
        subscription_end: null,
        created_at: new Date()
      }
    },
    { upsert: true }
  );

  return userId;
};
