exports = async function(authEvent) {
  // This function is the Custom Authentication Provider.
  // It receives the authentication payload from the client.
  // The client sends { initData: "..." }

  const initData = authEvent.initData;
  if (!initData) {
    throw new Error("Missing initData");
  }

  // Parse initData
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get("hash");
  urlParams.delete("hash");

  // Sort keys
  const keys = Array.from(urlParams.keys()).sort();
  const dataCheckString = keys.map(key => `${key}=${urlParams.get(key)}`).join("\n");

  // Get Bot Token from Values
  const botToken = context.values.get("telegram_bot_token");
  if (!botToken) {
    throw new Error("Bot token not configured");
  }

  // Calculate HMAC-SHA-256
  const crypto = require("crypto");
  const secretKey = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData signature");
  }

  // Extract User Info
  const userStr = urlParams.get("user");
  const userData = JSON.parse(userStr);

  // Return the user's ID as the unique identifier
  // This ID will be used as the internal user ID in App Services
  return { id: userData.id.toString(), name: userData.first_name };
};
