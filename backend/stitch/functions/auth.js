exports = function(loginPayload) {
  const crypto = require('crypto');

  // Get the bot token from Stitch Values (or hardcode for testing)
  // const botToken = context.values.get("botToken");
  const botToken = "8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY"; // Use Value in production

  const initData = loginPayload.initData;
  if (!initData) {
    throw new Error("No initData provided");
  }

  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  params.delete('hash');

  // Sort keys
  const keys = Array.from(params.keys()).sort();
  const dataCheckString = keys.map(key => `${key}=${params.get(key)}`).join('\n');

  // Calculate Hash
  const secretKey = crypto.createHmac('sha256', 'WebAppData')
    .update(botToken)
    .digest();

  const calculatedHash = crypto.createHmac('sha256', secretKey)
    .update(dataCheckString)
    .digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData hash");
  }

  // Parse user data
  const userStr = params.get('user');
  const user = JSON.parse(userStr);

  // Return the user's Telegram ID as their Stitch ID
  return {
    id: user.id.toString(),
    name: user.first_name,
    username: user.username,
    photo_url: user.photo_url
  };
};
