exports = async function(authEvent) {
  const crypto = require("crypto");

  // 1. Get the initData from the request headers or body
  // In Custom Function Auth, the payload is in authEvent.data
  const initData = authEvent.data.initData;

  if (!initData) {
    throw new Error("Missing initData");
  }

  // 2. Validate the initData using HMAC-SHA-256
  // See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get("hash");
  urlParams.delete("hash");
  urlParams.sort();

  let dataCheckString = "";
  for (const [key, value] of urlParams) {
    dataCheckString += `${key}=${value}\n`;
  }
  dataCheckString = dataCheckString.slice(0, -1);

  const botToken = context.values.get("telegramBotToken"); // Store your bot token in App Services Values
  if (!botToken) {
    throw new Error("Bot token not configured");
  }

  const secretKey = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (calculatedHash !== hash) {
    throw new Error("Invalid hash");
  }

  // 3. Extract user info
  const userJson = urlParams.get("user");
  const userData = JSON.parse(userJson);
  const userId = userData.id.toString();

  // 4. Upsert user in database
  const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const existingUser = await users.findOne({ _id: userId });

  if (!existingUser) {
    // New User - Apply Referral Logic if needed
    let balance = 50; // Welcome bonus
    let referrerId = null;

    // Check for referral (start_param)
    const startParam = urlParams.get("start_param");
    if (startParam && startParam !== userId) {
      // Basic check if referrer exists
      const referrer = await users.findOne({ _id: startParam });
      if (referrer) {
        referrerId = startParam;
        // Bonus for referrer
        await users.updateOne(
          { _id: referrerId },
          {
            $inc: { balance: 25, referrals_count: 1 },
            // Logic to extend subscription for referrer if needed (simplified here)
          }
        );
      }
    }

    await users.insertOne({
      _id: userId,
      username: userData.username,
      first_name: userData.first_name,
      balance: balance,
      subscription_end: null,
      referrals_count: 0,
      referred_by: referrerId,
      created_at: new Date(),
      used_configs: []
    });
  } else {
    // Update user info if changed
    await users.updateOne(
      { _id: userId },
      { $set: { username: userData.username, first_name: userData.first_name, last_login: new Date() } }
    );
  }

  // 5. Return the user ID for the session
  return userId;
};
