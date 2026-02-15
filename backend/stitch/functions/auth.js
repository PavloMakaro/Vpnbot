exports = async function(initData) {
  // Validate input
  if (!initData) {
    throw new Error("Missing initData");
  }

  // Get bot token from context values (secrets)
  const botToken = context.values.get("BOT_TOKEN");
  if (!botToken) {
    throw new Error("BOT_TOKEN not configured in App Services");
  }

  // Parse initData string
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get("hash");
  if (!hash) {
    throw new Error("Missing hash in initData");
  }

  urlParams.delete("hash");

  // Sort keys alphabetically
  const params = [];
  for (const [key, value] of urlParams.entries()) {
    params.push(`${key}=${value}`);
  }
  params.sort();

  const dataCheckString = params.join("\n");

  // Validate hash using HMAC-SHA-256
  const crypto = require("crypto");
  const secretKey = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();
  const calculatedHash = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData hash");
  }

  // Check auth_date for replay attacks (optional but recommended)
  const authDate = parseInt(urlParams.get("auth_date"));
  const now = Math.floor(Date.now() / 1000);
  if (now - authDate > 86400) { // 24 hours
    throw new Error("initData is too old");
  }

  // Parse user data
  const userJson = urlParams.get("user");
  if (!userJson) {
    throw new Error("Missing user data in initData");
  }
  const telegramUser = JSON.parse(userJson);
  const userId = telegramUser.id.toString();

  // Database operations
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Check for referral logic
  const startParam = urlParams.get("start_param");
  let referralBonus = 0;
  let referrerId = null;

  const existingUser = await usersCollection.findOne({ _id: userId });

  if (!existingUser && startParam) {
    // New user with referral code
    referrerId = startParam;
    // Verify referrer exists
    const referrer = await usersCollection.findOne({ _id: referrerId });
    if (referrer && referrer._id !== userId) {
        // Apply bonus to referrer (e.g. 25 RUB + 7 days)
        // Note: Using constants from python code: 25 RUB, 7 days
        const bonusAmount = 25;
        const bonusDays = 7;

        let currentEnd = referrer.subscription_end ? new Date(referrer.subscription_end) : new Date();
        if (currentEnd < new Date()) currentEnd = new Date();
        currentEnd.setDate(currentEnd.getDate() + bonusDays);

        await usersCollection.updateOne(
            { _id: referrerId },
            {
                $inc: { balance: bonusAmount, referrals_count: 1 },
                $set: { subscription_end: currentEnd }
            }
        );
        referralBonus = 50; // Bonus for new user
    }
  } else if (!existingUser) {
      referralBonus = 50; // Standard welcome bonus? Or only referral? Python code says REFERRAL_BONUS_NEW_USER = 50 regardless?
      // Check python code: users_db[user_id] = {'balance': REFERRAL_BONUS_NEW_USER, ...}
      // Yes, new users get 50.
  }

  // Prepare user update/insert
  const updateDoc = {
    $set: {
      username: telegramUser.username,
      first_name: telegramUser.first_name,
      last_auth: new Date()
    },
    $setOnInsert: {
      balance: existingUser ? existingUser.balance : referralBonus,
      subscription_end: existingUser ? existingUser.subscription_end : null,
      referred_by: referrerId,
      referrals_count: 0,
      created_at: new Date()
    }
  };

  await usersCollection.updateOne({ _id: userId }, updateDoc, { upsert: true });

  // Fetch updated user to return
  const finalUser = await usersCollection.findOne({ _id: userId });

  return {
    id: userId,
    ...finalUser,
    subscription_active: finalUser.subscription_end ? new Date(finalUser.subscription_end) > new Date() : false
  };
};
