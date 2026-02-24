const crypto = require("crypto");

/**
 * Custom Function Authentication for Telegram Mini App
 *
 * Payload structure: { initData: "query_id=..." }
 */
exports = async function(payload) {
  const initData = payload.initData;
  if (!initData) {
    throw new Error("Missing initData");
  }

  const botToken = context.values.get("BOT_TOKEN");
  if (!botToken) {
    throw new Error("BOT_TOKEN value not configured in App Services");
  }

  // Parse initData
  const params = new URLSearchParams(initData);
  const hash = params.get("hash");
  if (!hash) {
    throw new Error("Missing hash in initData");
  }
  params.delete("hash");

  // Sort keys and create data-check-string
  const sortedKeys = Array.from(params.keys()).sort();
  const dataCheckString = sortedKeys.map(key => `${key}=${params.get(key)}`).join("\n");

  // Calculate secret key
  const secretKey = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();

  // Calculate hash
  const calculatedHash = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (calculatedHash !== hash) {
    throw new Error("Invalid hash");
  }

  // Parse user data
  const userJson = params.get("user");
  const userData = JSON.parse(userJson);
  const userId = userData.id.toString();

  // Upsert user in database
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Check if user exists to handle referral logic (only for new users)
  const existingUser = await usersCollection.findOne({ _id: userId });

  const updateDoc = {
    $set: {
      username: userData.username,
      first_name: userData.first_name,
      last_login: new Date()
    },
    $setOnInsert: {
      balance: 0, // Will be updated if referral exists
      subscription_end: null,
      referrals_count: 0,
      used_configs: [],
      created_at: new Date()
    }
  };

  // Handle Referral Logic
  if (!existingUser) {
    const startParam = params.get("start_param");
    if (startParam && startParam !== userId) {
      // Find referrer
      const referrer = await usersCollection.findOne({ _id: startParam });
      if (referrer) {
        // Bonus for new user
        updateDoc.$setOnInsert.balance = 50; // REFERRAL_BONUS_NEW_USER
        updateDoc.$setOnInsert.referred_by = startParam;

        // Bonus for referrer (Transactional update preferred, but simple update for now)
        await usersCollection.updateOne(
          { _id: startParam },
          {
            $inc: { balance: 25, referrals_count: 1 }, // REFERRAL_BONUS_REFERRER
            // Extend subscription for referrer
             // Logic for date extension is complex in simple update, skipping for auth function speed
             // Ideally this should be a separate Trigger or Function call
          }
        );

        // Complex logic: extending subscription date for referrer
        // Since we can't easily do date math in a simple updateOne without aggregation pipeline or read-modify-write
        // Let's do a read-modify-write for the referrer
        let currentEnd = referrer.subscription_end || new Date();
        if (currentEnd < new Date()) currentEnd = new Date();
        currentEnd.setDate(currentEnd.getDate() + 7); // REFERRAL_BONUS_DAYS

        await usersCollection.updateOne(
            { _id: startParam },
            { $set: { subscription_end: currentEnd } }
        );
      }
    }
  }

  await usersCollection.updateOne({ _id: userId }, updateDoc, { upsert: true });

  // Return the user identity for Realm
  return { id: userId, name: userData.username };
};
