exports = async function(loginPayload) {
    const { initData } = loginPayload;

    if (!initData) {
        throw new Error("Missing initData");
    }

    const crypto = require('crypto');
    const botToken = context.values.get("BOT_TOKEN");

    if (!botToken) {
        console.error("BOT_TOKEN is not configured in environment values.");
        throw new Error("Internal Server Error");
    }

    // Parse initData
    const urlParams = new URLSearchParams(initData);
    const hash = urlParams.get('hash');

    if (!hash) {
        throw new Error("Invalid initData: missing hash");
    }

    urlParams.delete('hash');

    // Sort parameters alphabetically
    const params = Array.from(urlParams.entries());
    params.sort((a, b) => a[0].localeCompare(b[0]));

    // Construct data check string
    const dataCheckString = params.map(([key, value]) => `${key}=${value}`).join('\n');

    // Create secret key using HMAC-SHA256 of the bot token with "WebAppData" as key
    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();

    // Calculate expected hash
    const expectedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

    if (hash !== expectedHash) {
        throw new Error("Invalid signature");
    }

    // Extract user data
    const userJson = urlParams.get('user');
    if (!userJson) {
         throw new Error("Invalid initData: missing user");
    }

    const tgUser = JSON.parse(userJson);
    const tgUserId = tgUser.id.toString();

    // Upsert user in database
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCollection = db.collection("users");

    // Attempt to update existing, or set defaults for new user
    await usersCollection.updateOne(
        { _id: tgUserId },
        {
            $set: {
                username: tgUser.username || "",
                first_name: tgUser.first_name || "",
                last_name: tgUser.last_name || ""
            },
            $setOnInsert: {
                balance: 50, // Welcome bonus matching Python legacy code
                subscription_end: null,
                referred_by: null,
                referrals_count: 0,
                used_configs: []
            }
        },
        { upsert: true }
    );

    return tgUserId;
};