exports = async function(payload) {
  // payload is { initData: "..." } from Realm.Credentials.function
  const authData = payload.initData;

  const crypto = require('crypto');
  const BOT_TOKEN = context.values.get("BOT_TOKEN"); // Store bot token in Values

  if (!authData) {
    throw new Error("No initData provided");
  }

  // Parse initData
  const params = new URLSearchParams(authData);
  const hash = params.get("hash");
  params.delete("hash");

  // Validate hash
  const dataCheckString = Array.from(params.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");

  const secretKey = crypto.createHmac("sha256", "WebAppData")
    .update(BOT_TOKEN)
    .digest();

  const calculatedHash = crypto.createHmac("sha256", secretKey)
    .update(dataCheckString)
    .digest("hex");

  if (calculatedHash !== hash) {
    throw new Error("Invalid authentication data");
  }

  // User is valid
  const user = JSON.parse(params.get("user"));
  const startParam = params.get("start_param");
  const userIdStr = user.id.toString();

  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Check if user exists
  let userDoc = await usersCollection.findOne({ _id: userIdStr });

  if (!userDoc) {
    // New user
    const newUser = {
      _id: userIdStr,
      username: user.username,
      first_name: user.first_name,
      last_name: user.last_name,
      balance: 50, // Welcome bonus
      subscription_end: null,
      referrals_count: 0,
      referred_by: startParam ? startParam : null,
      created_at: new Date()
    };

    // Handle referral bonus
    if (startParam && startParam !== userIdStr) {
      const referrer = await usersCollection.findOne({ _id: startParam });
      if (referrer) {
        await usersCollection.updateOne(
          { _id: startParam },
          {
            $inc: { balance: 25, referrals_count: 1 },
            $push: { referrals: userIdStr }
          }
        );
        // Bonus subscription days for referrer
        let newSubEnd = referrer.subscription_end ? new Date(referrer.subscription_end) : new Date();
        if (newSubEnd < new Date()) newSubEnd = new Date();
        newSubEnd.setDate(newSubEnd.getDate() + 7);

        await usersCollection.updateOne(
          { _id: startParam },
          { $set: { subscription_end: newSubEnd } }
        );
      }
    }

    await usersCollection.insertOne(newUser);
  } else {
    // Update user info
    await usersCollection.updateOne(
      { _id: userIdStr },
      { $set: {
          username: user.username,
          first_name: user.first_name,
          last_name: user.last_name,
          last_login: new Date()
        }
      }
    );
  }

  // Return user ID string for Realm Custom Function Auth
  return userIdStr;
};
