exports = async function(loginPayload) {
    const crypto = require("crypto");

    // Get token from context values
    const botToken = context.values.get("BOT_TOKEN");
    if (!botToken) {
        throw new Error("BOT_TOKEN is not configured.");
    }

    const initData = loginPayload.initData;
    if (!initData) {
        throw new Error("No initData provided");
    }

    const urlParams = new URLSearchParams(initData);
    const hash = urlParams.get('hash');
    urlParams.delete('hash');

    // Sort parameters alphabetically
    const dataToCheck = [];
    urlParams.sort();
    for (const [key, value] of urlParams.entries()) {
        dataToCheck.push(`${key}=${value}`);
    }
    const dataCheckString = dataToCheck.join('\n');

    // Calculate secret key and HMAC
    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
    const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

    if (calculatedHash !== hash) {
        throw new Error("Invalid initData hash");
    }

    // Hash is valid, extract user
    const userStr = urlParams.get('user');
    if (!userStr) {
        throw new Error("No user data found in initData");
    }
    const user = JSON.parse(userStr);

    // Get users collection
    const cluster = context.services.get("mongodb-atlas");
    const db = cluster.db("vpn_bot");
    const users = db.collection("users");

    const userIdStr = user.id.toString();

    // Upsert user profile
    const updateResult = await users.updateOne(
        { _id: userIdStr },
        {
            $set: {
                username: user.username || "N/A",
                first_name: user.first_name || "N/A",
                last_login: new Date()
            },
            $setOnInsert: {
                balance: 50, // Welcome bonus matching python code
                subscription_end: null,
                referrals_count: 0,
                used_configs: []
            }
        },
        { upsert: true }
    );

    return userIdStr;
};
