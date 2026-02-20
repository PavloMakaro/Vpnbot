exports = function(loginPayload) {
  // loginPayload contains { id, initData } provided by the client SDK
  const crypto = require('crypto');

  const botToken = context.values.get("botToken"); // Set this in App Services > Values
  if (!botToken) {
    throw new Error("Bot token not configured");
  }

  const initData = loginPayload.initData;
  if (!initData) {
    throw new Error("No initData provided");
  }

  // Parse initData string into an object
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get("hash");
  urlParams.delete("hash");

  // Sort keys alphabetically
  const dataCheckString = Array.from(urlParams.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");

  // Verify signature
  const secretKey = crypto.createHmac('sha256', "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid signature");
  }

  // Check expiration (optional but recommended)
  const authDate = parseInt(urlParams.get("auth_date"));
  const now = Math.floor(Date.now() / 1000);
  if (now - authDate > 86400) { // 24 hours
    throw new Error("Data is outdated");
  }

  // Return the user ID (Telegram ID)
  const user = JSON.parse(urlParams.get("user"));
  return user.id.toString();
};
