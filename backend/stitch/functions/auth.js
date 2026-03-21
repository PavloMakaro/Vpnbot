exports = async function(loginPayload) {
  const crypto = require("crypto");
  const initData = loginPayload.initData;

  // WARNING: Never include development bypasses here.
  if (!initData) {
      throw new Error("Missing initData");
  }

  // Parse initData
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get("hash");
  urlParams.delete("hash");
  urlParams.sort();

  let dataCheckString = "";
  for (const [key, value] of urlParams.entries()) {
      dataCheckString += `${key}=${value}\n`;
  }
  dataCheckString = dataCheckString.slice(0, -1);

  const BOT_TOKEN = context.values.get("BOT_TOKEN");
  const secretKey = crypto.createHmac("sha256", "WebAppData").update(BOT_TOKEN).digest();
  const calculatedHash = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (calculatedHash !== hash) {
      throw new Error("Invalid initData signature");
  }

  const user = JSON.parse(urlParams.get("user"));
  const telegramId = user.id.toString();

  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Upsert user profile
  await collection.updateOne(
      { telegram_id: telegramId },
      {
          $set: {
              telegram_id: telegramId,
              username: user.username,
              first_name: user.first_name,
              last_login: new Date()
          },
          $setOnInsert: {
              balance: 50, // Initial bonus
              subscription_end: null,
              used_configs: [],
              referrals_count: 0
          }
      },
      { upsert: true }
  );

  return telegramId;
};