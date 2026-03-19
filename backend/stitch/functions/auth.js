exports = async function(loginPayload) {
    const crypto = require("crypto");

    // Telegram Bot Token (Must be stored as a Secret and linked via Context Values)
    // NEVER hardcode this in production.
    const botToken = context.values.get("BOT_TOKEN") || process.env.BOT_TOKEN;

    if (!botToken) {
        console.error("Missing BOT_TOKEN context value");
        throw new Error("Internal Server Error: Missing Configuration");
    }

    const initData = loginPayload.initData;
    if (!initData) {
        throw new Error("Missing initData payload");
    }

    // Parse initData URL query string
    const urlParams = new URLSearchParams(initData);
    const hash = urlParams.get('hash');

    if (!hash) {
        throw new Error("Missing hash in initData");
    }

    urlParams.delete('hash');

    // Create data check string by sorting keys
    const keys = Array.from(urlParams.keys()).sort();
    const dataCheckString = keys.map(key => `${key}=${urlParams.get(key)}`).join('\n');

    // Compute HMAC
    const secretKey = crypto.createHmac('sha256', "WebAppData").update(botToken).digest();
    const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

    if (calculatedHash !== hash) {
        console.error(`Hash mismatch. Expected: ${hash}, Calculated: ${calculatedHash}`);
        // NOTE: NEVER bypass this validation! It is a critical security vulnerability.
        throw new Error("Invalid initialization data signature");
    }

    // Extract User Data
    const userStr = urlParams.get('user');
    if (!userStr) {
        throw new Error("Missing user object in initData");
    }

    let tgUser;
    try {
        tgUser = JSON.parse(userStr);
    } catch (e) {
        throw new Error("Invalid user JSON string");
    }

    const tgUserId = tgUser.id.toString();

    // Database Operations: Upsert User Profile
    const mongodb = context.services.get("mongodb-atlas");
    const usersCollection = mongodb.db("vpn_bot").collection("users");

    // Upsert the user profile data
    await usersCollection.updateOne(
        { _id: tgUserId },
        {
            $set: {
                username: tgUser.username || "N/A",
                first_name: tgUser.first_name || "N/A",
                last_auth_date: new Date()
            },
            $setOnInsert: {
                balance: 50, // Initial referral bonus from legacy code
                subscription_end: null,
                referrals_count: 0,
                used_configs: []
            }
        },
        { upsert: true }
    );

    console.log(`Successfully authenticated Telegram user: ${tgUserId}`);
    return tgUserId; // Returns the user ID to link identities in Atlas
};
