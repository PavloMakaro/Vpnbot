exports = async function(loginPayload) {
  // Authentication function for Custom Function Auth Provider
  // The client sends { initData: "..." }

  const crypto = require('crypto');

  // Retrieve the bot token from Values (Stitch Secrets)
  // In Atlas App Services, use context.values.get("telegramBotToken");
  const botToken = context.values.get("telegramBotToken");

  if (!botToken) {
    throw new Error("Bot token secret not configured in Atlas App Services");
  }

  const initData = loginPayload.initData;
  if (!initData) {
    throw new Error("No initData provided");
  }

  // Parse query string
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get('hash');

  if (!hash) {
      throw new Error("No hash provided");
  }

  urlParams.delete('hash');

  // Sort keys alphabetically
  const dataCheckString = Array.from(urlParams.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');

  // HMAC-SHA-256 signature verification
  const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid signature");
  }

  // Extract user info
  const userStr = urlParams.get('user');
  if (!userStr) {
      throw new Error("No user data in initData");
  }

  const user = JSON.parse(userStr);
  const userId = user.id.toString();

  // Return the user's ID as the Realm User ID.
  // We can also return extra metadata if needed, but the ID is key.
  return { id: userId, name: user.first_name, username: user.username };
};
