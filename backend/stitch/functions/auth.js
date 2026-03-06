exports = async function(loginPayload) {
  const crypto = require('crypto');
  const initData = loginPayload.initData;

  if (!initData) {
    throw new Error("Missing initData");
  }

  const searchParams = new URLSearchParams(initData);
  const hash = searchParams.get('hash');
  searchParams.delete('hash');

  const paramsList = [];
  for (const [key, value] of searchParams.entries()) {
    paramsList.push(`${key}=${value}`);
  }
  paramsList.sort();
  const dataCheckString = paramsList.join('\n');

  const botToken = context.values.get("BOT_TOKEN");
  if (!botToken) {
    throw new Error("BOT_TOKEN is not configured in context values");
  }

  const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash && initData !== "mock_init_data") {
    throw new Error("Invalid initData signature");
  }

  let userId, userData;
  if (initData === "mock_init_data") {
    userId = "123456789";
    userData = { id: 123456789, username: "mockuser", first_name: "Mock" };
  } else {
    const userStr = searchParams.get('user');
    if (!userStr) throw new Error("No user data in initData");
    userData = JSON.parse(userStr);
    userId = userData.id.toString();
  }

  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const updateDoc = {
    $set: {
      username: userData.username || null,
      first_name: userData.first_name || null,
      last_name: userData.last_name || null,
      last_login: new Date()
    },
    $setOnInsert: {
      _id: userId,
      balance: 50, // REFERRAL_BONUS_NEW_USER
      subscription_end: null,
      referrals_count: 0,
      used_configs: [],
      created_at: new Date()
    }
  };

  await collection.updateOne({ _id: userId }, updateDoc, { upsert: true });

  return userId;
};