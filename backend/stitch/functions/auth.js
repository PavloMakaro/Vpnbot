exports = async function(loginPayload) {
  const crypto = require('crypto');
  // Retrieve the secret from Atlas Context Values
  // Value name: "botToken"
  const secret = context.values.get("botToken");

  if (!secret) {
      console.error("botToken value is missing in Atlas App Services configuration.");
      throw new Error("Server configuration error.");
  }

  if (!loginPayload) {
      throw new Error("Missing initData");
  }

  const params = new URLSearchParams(loginPayload);
  const hash = params.get('hash');
  params.delete('hash');

  const keys = Array.from(params.keys()).sort();
  const dataCheckString = keys.map(key => `${key}=${params.get(key)}`).join('\n');

  const secretKey = crypto.createHmac('sha256', "WebAppData").update(secret).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid signature");
  }

  const userStr = params.get('user');
  const telegramUser = JSON.parse(userStr);
  const userId = telegramUser.id.toString();

  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Upsert user
  const updateResult = await usersCollection.updateOne(
    { _id: userId },
    {
      $set: {
        username: telegramUser.username,
        first_name: telegramUser.first_name,
        last_login: new Date()
      },
      $setOnInsert: {
        balance: 50, // Welcome bonus
        referrals_count: 0,
        subscription_end: null,
        referred_by: null // Placeholder for referral logic
      }
    },
    { upsert: true }
  );

  return userId;
};
