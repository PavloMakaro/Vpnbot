exports = function(loginPayload) {
  // loginPayload should contain the Telegram initData string passed from the client
  // e.g. "query_id=...&user=...&auth_date=...&hash=..."
  const initData = loginPayload.initData;
  if (!initData) {
    throw new Error("Missing initData");
  }

  // Parse query string manually to ensure correct sorting and handling
  // The string is likely URL encoded, so decodeURI might be needed, but URLSearchParams handles it.
  const params = new URLSearchParams(initData);
  const dataCheckArr = [];
  let hash = "";

  params.forEach((value, key) => {
    if (key === "hash") {
      hash = value;
    } else {
      dataCheckArr.push(`${key}=${value}`);
    }
  });

  if (!hash) {
      throw new Error("No hash provided");
  }

  // Sort alphabetically
  dataCheckArr.sort();
  const dataCheckString = dataCheckArr.join("\n");

  // Verify signature
  // Note: Ensure the 'crypto' module is available in your Function environment (Node.js)
  const crypto = require('crypto');

  // Value name: "telegramBotToken" must be set in App Services > Values
  const botToken = context.values.get("telegramBotToken");

  if (!botToken) {
    throw new Error("Bot token not configured in Values");
  }

  // HMAC-SHA-256 signature
  const secretKey = crypto.createHmac('sha256', "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid signature");
  }

  // Signature valid. Return the user identity.
  const userStr = params.get("user");
  if (!userStr) {
      throw new Error("No user data found");
  }
  const userObj = JSON.parse(userStr);

  // Return an object representing the user. This object becomes `context.user.data` in other functions.
  return {
    id: userObj.id.toString(),
    username: userObj.username,
    first_name: userObj.first_name,
    language_code: userObj.language_code
  };
};
