exports = async function(loginPayload) {
  // Extract and parse Telegram initData
  const initData = loginPayload.initData;
  if (!initData) {
    throw new Error("Missing initData");
  }

  // Parse query string into an object and handle the URI encoding
  const urlParams = new URLSearchParams(initData);
  const data = Object.fromEntries(urlParams.entries());

  if (!data.hash) {
    throw new Error("Missing hash in initData");
  }

  const hash = data.hash;
  delete data.hash;

  // Sort keys alphabetically
  const keys = Object.keys(data).sort();
  const dataCheckString = keys.map(k => `${k}=${data[k]}`).join('\n');

  // Verify HMAC-SHA-256
  // Requires "crypto" node module enabled in App Services
  const crypto = require('crypto');
  const botToken = context.values.get("BOT_TOKEN");
  if (!botToken) {
    throw new Error("Server configuration error: BOT_TOKEN not found.");
  }

  const secretKey = crypto.createHmac('sha256', "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid hash - Authentication failed.");
  }

  // Parse user object
  const userStr = data.user;
  if (!userStr) {
    throw new Error("Missing user data");
  }

  let tgUser;
  try {
    tgUser = JSON.parse(userStr);
  } catch (e) {
    throw new Error("Failed to parse user data");
  }

  const userId = tgUser.id.toString();

  // Connect to DB
  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  // Upsert user into database
  const updateDoc = {
    $set: {
      username: tgUser.username || "N/A",
      first_name: tgUser.first_name || "N/A",
      last_login: new Date()
    },
    $setOnInsert: {
      balance: 50, // REFERRAL_BONUS_NEW_USER
      subscription_end: null,
      referrals_count: 0,
      used_configs: [],
      created_at: new Date()
    }
  };

  // Handle referral if start_param exists (from t.me/bot?start=123)
  if (data.start_param) {
      const referrerId = data.start_param;
      if (referrerId !== userId) { // Prevent self-referral
          const referrer = await usersCollection.findOne({ _id: referrerId });
          // Only apply if user is new
          const existingUser = await usersCollection.findOne({ _id: userId });

          if (referrer && !existingUser) {
              updateDoc.$setOnInsert.referred_by = referrerId;

              // Give bonus to referrer
              const REFERRAL_BONUS_REFERRER = 25;
              const REFERRAL_BONUS_DAYS = 7;

              const now = new Date();
              let newEnd = new Date();

              if (referrer.subscription_end) {
                  const currentEnd = new Date(referrer.subscription_end);
                  if (currentEnd > now) {
                      newEnd = new Date(currentEnd.getTime() + (REFERRAL_BONUS_DAYS * 24 * 60 * 60 * 1000));
                  } else {
                      newEnd = new Date(now.getTime() + (REFERRAL_BONUS_DAYS * 24 * 60 * 60 * 1000));
                  }
              } else {
                 newEnd = new Date(now.getTime() + (REFERRAL_BONUS_DAYS * 24 * 60 * 60 * 1000));
              }

              await usersCollection.updateOne(
                  { _id: referrerId },
                  {
                      $inc: {
                          balance: REFERRAL_BONUS_REFERRER,
                          referrals_count: 1
                      },
                      $set: {
                          subscription_end: newEnd
                      }
                  }
              );
          }
      }
  }

  await usersCollection.updateOne(
    { _id: userId },
    updateDoc,
    { upsert: true }
  );

  // Return the unique identifier for Custom Function Auth
  return userId.toString();
};