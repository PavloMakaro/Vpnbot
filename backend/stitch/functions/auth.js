exports = function(loginPayload) {
  const crypto = require('crypto');
  const secret = context.values.get("TELEGRAM_BOT_TOKEN");

  if (!secret) {
    throw new Error("Bot token not configured");
  }

  // 1. Parse the query string
  const params = new URLSearchParams(loginPayload);
  const hash = params.get("hash");
  params.delete("hash");

  // 2. Sort keys
  const keys = Array.from(params.keys()).sort();

  // 3. Create data check string
  const dataCheckString = keys.map(key => `${key}=${params.get(key)}`).join("\n");

  // 4. Calculate HMAC
  const secretKey = crypto.createHmac('sha256', "WebAppData").update(secret).digest();
  const hmac = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  // 5. Compare
  if (hmac !== hash) {
    throw new Error("Invalid signature");
  }

  // 6. Return user identity (and create/update user in DB)
  const userData = JSON.parse(params.get("user"));
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  usersCollection.updateOne(
    { _id: userData.id.toString() },
    {
      $set: {
        username: userData.username,
        first_name: userData.first_name,
        last_login: new Date()
      },
      $setOnInsert: {
        balance: 0,
        subscription_end: null,
        referrals_count: 0,
        referred_by: null,
        created_at: new Date()
      }
    },
    { upsert: true }
  );

  return { id: userData.id.toString(), name: userData.first_name };
};
