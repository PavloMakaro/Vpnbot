exports = function(loginPayload) {
  const crypto = require('crypto');
  const BOT_TOKEN = context.values.get("BOT_TOKEN");

  if (!BOT_TOKEN) {
      console.error("BOT_TOKEN not set in context values");
      throw new Error("Internal server error");
  }

  const initData = loginPayload.initData;
  if (!initData) {
      throw new Error("No initData provided");
  }

  // Parse initData
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');
  urlParams.delete('hash');

  // Create data check string
  const dataCheckString = Array.from(urlParams.keys())
      .sort()
      .map(key => `${key}=${urlParams.get(key)}`)
      .join('\n');

  // Validate hash
  const secretKey = crypto.createHmac('sha256', 'WebAppData').update(BOT_TOKEN).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
      throw new Error("Invalid initData hash");
  }

  // Return Telegram User ID as the Realm User ID
  const user = JSON.parse(urlParams.get('user'));
  return user.id.toString();
};
