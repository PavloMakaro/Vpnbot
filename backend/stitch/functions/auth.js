exports = function(payload) {
  const crypto = require('crypto');
  const botToken = context.values.get("telegramBotToken");

  if (!payload || !payload.initData) {
    throw new Error("Missing initData");
  }

  const initData = payload.initData;
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get("hash");
  urlParams.delete("hash");

  const keys = Array.from(urlParams.keys()).sort();
  const dataCheckString = keys.map(key => `${key}=${urlParams.get(key)}`).join("\n");

  const secretKey = crypto.createHmac('sha256', "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash === hash) {
    const user = JSON.parse(urlParams.get("user"));

    // Upsert user in database
    const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
    users.updateOne(
      { _id: user.id.toString() },
      {
        $set: {
          username: user.username,
          first_name: user.first_name,
          last_login: new Date()
        },
        $setOnInsert: {
          balance: 0,
          subscription_end: null,
          referrals_count: 0,
          used_configs: []
        }
      },
      { upsert: true }
    );

    return user.id.toString();
  } else {
    throw new Error("Invalid signature");
  }
};
