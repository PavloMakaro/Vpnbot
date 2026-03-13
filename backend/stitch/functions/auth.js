exports = async function(loginPayload) {
    const crypto = require("crypto");
    const { initData } = loginPayload;
    if (!initData) {
        throw new Error("Missing initData");
    }

    const paramsMap = new Map();
    initData.split('&').forEach(pair => {
        const [key, val] = pair.split('=');
        paramsMap.set(decodeURIComponent(key), decodeURIComponent(val));
    });

    const hash = paramsMap.get('hash');
    paramsMap.delete('hash');

    const params = [];
    for (const [key, val] of paramsMap.entries()) {
        params.push(`${key}=${val}`);
    }
    params.sort();
    const dataCheckString = params.join('\n');

    const botToken = context.values.get("BOT_TOKEN");
    if (!botToken) {
        throw new Error("BOT_TOKEN not found in context values");
    }

    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
    const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

    if (calculatedHash !== hash) {
        throw new Error("Invalid initData hash");
    }

    const userStr = paramsMap.get('user');
    if (!userStr) {
        throw new Error("Missing user data");
    }

    const telegramUser = JSON.parse(userStr);
    const userId = telegramUser.id.toString();
    const username = telegramUser.username || "N/A";
    const firstName = telegramUser.first_name || "N/A";

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersColl = db.collection("users");

    await usersColl.updateOne(
        { _id: userId },
        {
            $set: {
                username: username,
                first_name: firstName,
                last_login: new Date()
            },
            $setOnInsert: {
                balance: 50,
                subscription_end: null,
                used_configs: [],
                referrals_count: 0
            }
        },
        { upsert: true }
    );

    return userId;
};
