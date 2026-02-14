exports = function(loginPayload) {
  // loginPayload should contain { initData: "..." }
  const crypto = require('crypto');

  const initData = loginPayload.initData;
  if (!initData) {
    throw new Error("No initData provided");
  }

  // Parse initData
  const params = new URLSearchParams(initData);
  const hash = params.get("hash");
  params.delete("hash");

  // Sort keys
  const keys = Array.from(params.keys()).sort();
  const dataCheckString = keys.map(key => `${key}=${params.get(key)}`).join("\n");

  // Get Bot Token from Context Values (Secrets)
  const BOT_TOKEN = context.values.get("telegramBotToken");
  if (!BOT_TOKEN) {
    throw new Error("Bot token not configured in values");
  }

  // Calculate HMAC
  const secretKey = crypto.createHmac('sha256', "WebAppData").update(BOT_TOKEN).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid signature");
  }

  // Parse user data
  const userStr = params.get("user");
  if (!userStr) {
    throw new Error("No user data in initData");
  }

  const user = JSON.parse(userStr);

  // Return the user ID as the authenticated ID
  return { id: String(user.id), name: user.first_name, data: user };
};
