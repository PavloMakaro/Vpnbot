exports = function(loginPayload) {
  const crypto = require('crypto');
  // In production, create a Value in Atlas App Services named "botToken"
  const botToken = context.values.get("botToken") || "8338675458:AAG2jYEwJjcmWZAcwSpF1QJWPsqV-h2MnKY";

  const { initData } = loginPayload;
  if (!initData) {
    throw new Error("No initData provided");
  }

  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get("hash");
  urlParams.delete("hash");

  const dataCheckString = Array.from(urlParams.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");

  const secretKey = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();
  const signature = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (hash !== signature) {
    throw new Error("Invalid signature");
  }

  // Parse user data
  const user = JSON.parse(urlParams.get("user"));

  // Upsert user in database
  const collection = context.services.get("mongodb-atlas").db("vpn_bot_db").collection("users");

  // Basic user document structure
  const updateDoc = {
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
  };

  // If referral code exists (e.g. start_param), handle it
  // Note: start_param is not always present in initData directly in the way we want,
  // but if passed, we could handle it. For now, basic auth.

  return collection.updateOne({ _id: user.id.toString() }, updateDoc, { upsert: true })
    .then(() => {
      return { id: user.id.toString(), name: user.first_name };
    });
};
