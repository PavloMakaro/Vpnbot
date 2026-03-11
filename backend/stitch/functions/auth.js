exports = async function(loginPayload) {
    const crypto = require("crypto");

    // Extract payload data
    const { initData, botToken } = loginPayload;

    if (!initData) {
        throw new Error("Missing initData");
    }

    // Since we can't easily access the Context Values inside Custom Auth function directly
    // we require passing the bot token or fetching it if possible.
    // However, best practice in Stitch Custom Auth is to either have the token in context values:
    const token = context.values.get("BOT_TOKEN");

    if (!token) {
        throw new Error("Server configuration error: BOT_TOKEN not found.");
    }

    // Parse initData
    const urlParams = new URLSearchParams(initData);
    const hash = urlParams.get('hash');
    urlParams.delete('hash');

    // Sort parameters alphabetically
    const keys = Array.from(urlParams.keys()).sort();
    const dataCheckString = keys.map(key => `${key}=${urlParams.get(key)}`).join('\n');

    // Calculate HMAC-SHA-256
    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(token).digest();
    const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

    if (calculatedHash !== hash) {
        throw new Error("Authentication failed: Invalid hash");
    }

    // Data is verified, parse user info
    const userStr = urlParams.get('user');
    if (!userStr) {
        throw new Error("Missing user data in initData");
    }

    const userData = JSON.parse(userStr);
    const userId = userData.id.toString();

    // Upsert user into the 'users' collection
    const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

    await collection.updateOne(
        { _id: userId },
        {
            $set: {
                username: userData.username || 'N/A',
                first_name: userData.first_name || 'N/A',
                last_auth: new Date()
            },
            $setOnInsert: {
                balance: 0,
                subscription_end: null,
                used_configs: [],
                referrals_count: 0
            }
        },
        { upsert: true }
    );

    // Return the user ID as a string, which is used as the Realm User ID
    return userId;
};
