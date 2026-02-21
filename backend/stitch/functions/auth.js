exports = function(loginPayload) {
  // loginPayload contains the 'initData' string from Telegram WebApp
  const { initData } = loginPayload;

  if (!initData) {
    throw new Error("No initData provided");
  }

  const crypto = require('crypto');
  const BOT_TOKEN = context.values.get("BOT_TOKEN"); // Set this in Atlas App Services -> Values

  if (!BOT_TOKEN) {
      throw new Error("BOT_TOKEN value not configured in App Services");
  }

  // Parse initData
  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  params.delete('hash');

  // Sort keys alphabetically
  const sortedKeys = Array.from(params.keys()).sort();
  const dataCheckString = sortedKeys.map(key => `${key}=${params.get(key)}`).join('\n');

  // HMAC-SHA-256
  const secretKey = crypto.createHmac('sha256', 'WebAppData').update(BOT_TOKEN).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid Telegram data");
  }

  // Data is valid
  const userStr = params.get('user');
  const user = JSON.parse(userStr);

  // Upsert user in database
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Check if user exists to handle referral logic if new
  // Note: For referral logic to work perfectly here, we might need a separate function or pass start_param
  // But for Auth, we just ensure the user document exists.

  const telegramId = user.id.toString();

  // We use findOneAndUpdate to ensure atomic upsert
  // But we can't easily execute complex logic (like referral bonus) inside an Auth function
  // without side effects.
  // It's better to return the ID and let the client call 'initUser' or similar if needed,
  // OR just upsert basic info here.

  const doc = collection.findOneAndUpdate(
      { telegram_id: telegramId },
      {
          $set: {
              first_name: user.first_name,
              username: user.username,
              last_auth: new Date()
          },
          $setOnInsert: {
              telegram_id: telegramId,
              balance: 0, // Default balance
              referral_count: 0,
              created_at: new Date()
              // Referral logic should be handled separately if 'start_param' is present in initData
          }
      },
      { upsert: true, returnNewDocument: true }
  );

  return telegramId; // Returns the unique user ID for Atlas to use
};
