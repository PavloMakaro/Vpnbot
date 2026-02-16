exports = async function(loginPayload) {
  // 1. Get Dependencies and Secrets
  const crypto = require("crypto");
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Retrieve Bot Token from Values
  let BOT_TOKEN;
  try {
    BOT_TOKEN = context.values.get("BOT_TOKEN");
  } catch(e) {
    throw new Error("BOT_TOKEN not configured in Atlas Values");
  }

  const initData = loginPayload.initData;
  if (!initData) {
    throw new Error("Missing initData");
  }

  // 2. Parse initData
  const urlParams = new URLSearchParams(initData);
  const hash = urlParams.get("hash");
  urlParams.delete("hash");

  // Sort keys
  const paramsList = [];
  for (const [key, value] of urlParams.entries()) {
    paramsList.push(`${key}=${value}`);
  }
  paramsList.sort();
  const dataCheckString = paramsList.join("\n");

  // 3. Validate Hash
  const secretKey = crypto.createHmac("sha256", "WebAppData").update(BOT_TOKEN).digest();
  const computedHash = crypto.createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  if (computedHash !== hash) {
    throw new Error("Invalid initData hash");
  }

  // 4. Extract User Data
  const userStr = urlParams.get("user");
  if (!userStr) throw new Error("No user data found");

  const telegramUser = JSON.parse(userStr);
  const userId = telegramUser.id.toString();

  // 5. Check for Referral
  const startParam = urlParams.get("start_param");
  let referrerId = null;

  // 6. Upsert User
  const existingUser = await usersCollection.findOne({ _id: userId });

  let updateOp = {
    $set: {
      username: telegramUser.username,
      first_name: telegramUser.first_name,
      last_active: new Date()
    },
    $setOnInsert: {
      balance: 50, // Welcome bonus
      referral: { count: 0, earnings: 0 },
      used_configs: [],
      subscription_end: null
    }
  };

  if (!existingUser && startParam && startParam !== userId) {
    const referrer = await usersCollection.findOne({ _id: startParam });
    if (referrer) {
      referrerId = startParam;
      updateOp.$setOnInsert.referred_by = referrerId;

      const now = new Date();
      let newSubEnd = referrer.subscription_end ? new Date(referrer.subscription_end) : now;
      if (newSubEnd < now) newSubEnd = now;
      newSubEnd.setDate(newSubEnd.getDate() + 7);

      await usersCollection.updateOne(
        { _id: referrerId },
        {
          $inc: { "balance": 25, "referral.count": 1, "referral.earnings": 25 },
          $set: { subscription_end: newSubEnd }
        }
      );
    }
  }

  await usersCollection.updateOne(
    { _id: userId },
    updateOp,
    { upsert: true }
  );

  // Return the user ID to establish the session
  return userId;
};
