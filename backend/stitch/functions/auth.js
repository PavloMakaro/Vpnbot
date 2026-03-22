exports = async function(loginPayload) {
    const crypto = require("crypto");

    // Ensure we are getting the query string properly from the context or loginPayload
    const initDataString = loginPayload.initData || loginPayload;
    if (!initDataString || typeof initDataString !== 'string') {
        throw new Error("Missing or invalid initData");
    }

    // Parse the query string
    const urlParams = new URLSearchParams(initDataString);
    const hash = urlParams.get('hash');

    if (!hash) {
        throw new Error("Missing hash in initData");
    }

    // Remove hash from the params to reconstruct the data-check-string
    urlParams.delete('hash');

    // Sort keys alphabetically
    const keys = Array.from(urlParams.keys()).sort();

    // Construct the data-check-string
    const dataCheckString = keys.map(key => `${key}=${urlParams.get(key)}`).join('\n');

    // Get the bot token from context values
    const botToken = context.values.get("BOT_TOKEN");
    if (!botToken) {
        throw new Error("BOT_TOKEN context value is not set");
    }

    // Create secret key
    const secretKey = crypto.createHmac('sha256', 'WebAppData')
        .update(botToken)
        .digest();

    // Calculate hash
    const calculatedHash = crypto.createHmac('sha256', secretKey)
        .update(dataCheckString)
        .digest('hex');

    if (calculatedHash !== hash) {
        throw new Error("Invalid initData hash");
    }

    // Extract user JSON
    const userJsonStr = urlParams.get('user');
    if (!userJsonStr) {
        throw new Error("Missing user data");
    }

    let userData;
    try {
        userData = JSON.parse(userJsonStr);
    } catch (e) {
        throw new Error("Invalid user JSON");
    }

    const telegramId = userData.id.toString();

    // Upsert user data into the database
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCollection = db.collection("users");

    await usersCollection.updateOne(
        { _id: telegramId },
        {
            $set: {
                username: userData.username || "",
                first_name: userData.first_name || "",
                last_name: userData.last_name || "",
                last_login: new Date()
            },
            $setOnInsert: {
                balance: 0,
                subscription_end: null,
                referrals_count: 0,
                used_configs: [],
                registered_at: new Date()
            }
        },
        { upsert: true }
    );

    // Return the required user identity string ID for Atlas
    return telegramId;
};
