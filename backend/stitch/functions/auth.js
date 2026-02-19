exports = function(loginPayload) {
  const crypto = require("crypto");
  const initData = loginPayload.initData;

  if (!initData) {
    throw new Error("Missing initData");
  }

  const params = new URLSearchParams(initData);
  const hash = params.get("hash");
  params.delete("hash");

  // Create data check string
  const dataCheckString = Array.from(params.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");

  // Get bot token
  const botToken = context.values.get("botToken");
  if (!botToken) {
    // Fallback for development/testing if value not set, but ideally should throw
    console.error("botToken value not found in context.values");
    throw new Error("Configuration error: botToken missing");
  }

  const secretKey = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (calculatedHash !== hash) {
    throw new Error("Invalid signature");
  }

  const userStr = params.get("user");
  if (!userStr) {
    throw new Error("Missing user data");
  }
  const user = JSON.parse(userStr);

  // Return the user ID as string. This becomes context.user.id
  return String(user.id);
};
