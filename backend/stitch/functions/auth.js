exports = async function(authEvent) {
  const crypto = require('crypto');

  // Get the Telegram Bot Token from environment values/secrets
  // In a real deployment, you'd use context.values.get("telegram_bot_token");
  const botToken = context.values.get("telegram_bot_token") || "YOUR_BOT_TOKEN";

  const initData = authEvent.initData;
  if (!initData) {
    throw new Error("No initData provided");
  }

  // Parse initData
  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  params.delete('hash');

  // Validate hash
  const dataCheckString = Array.from(params.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');

  const secretKey = crypto.createHmac('sha256', 'WebAppData')
    .update(botToken)
    .digest();

  const calculatedHash = crypto.createHmac('sha256', secretKey)
    .update(dataCheckString)
    .digest('hex');

  if (calculatedHash !== hash) {
    throw new Error("Invalid initData hash");
  }

  // Parse user data
  const userData = JSON.parse(params.get('user'));
  const telegramId = userData.id.toString();

  // Database access
  const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Check if user exists
  let user = await users.findOne({ _id: telegramId });

  const now = new Date();

  if (!user) {
    // New user logic
    const referrerId = params.get('start_param');
    let bonusBalance = 0;

    // Check referral
    if (referrerId && referrerId !== telegramId) {
      const referrer = await users.findOne({ _id: referrerId });
      if (referrer) {
        // Bonus for new user
        bonusBalance = 50; // Configurable

        // Bonus for referrer
        await users.updateOne(
          { _id: referrerId },
          {
            $inc: { balance: 25, referrals_count: 1 },
            // Add bonus days logic if needed, but simple balance increment is safer for now
          }
        );
      }
    }

    user = {
      _id: telegramId,
      username: userData.username,
      first_name: userData.first_name,
      balance: bonusBalance,
      subscription_end: null,
      referrals_count: 0,
      referred_by: referrerId || null,
      created_at: now,
      last_login: now
    };

    await users.insertOne(user);
  } else {
    // Update existing user
    await users.updateOne(
      { _id: telegramId },
      {
        $set: {
          last_login: now,
          username: userData.username,
          first_name: userData.first_name
        }
      }
    );
  }

  return { id: telegramId, name: userData.first_name };
};
