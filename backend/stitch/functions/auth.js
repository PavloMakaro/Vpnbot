exports = async function(loginPayload) {
    const crypto = require('crypto');

    // Get the bot token from Atlas Context Values
    const botToken = context.values.get("BOT_TOKEN");

    if (!botToken) {
        throw new Error("BOT_TOKEN is not configured in the environment.");
    }

    const initData = loginPayload.initData;

    try {
        let userData;

        // Handle mock initData for local testing (fallback logic)
        if (initData === "mock_init_data" || initData.startsWith("mock_")) {
            userData = {
                id: 123456789,
                first_name: "Test",
                username: "testuser"
            };
        } else {
            // Parse actual Telegram initData
            const parsedData = new URLSearchParams(initData);

            // Extract the hash and remove it from the data string for validation
            const receivedHash = parsedData.get('hash');
            if (!receivedHash) {
                throw new Error("Missing hash in initData");
            }

            parsedData.delete('hash');

            // Sort keys alphabetically
            const keys = Array.from(parsedData.keys()).sort();

            // Create data check string
            const dataCheckString = keys.map(key => `${key}=${parsedData.get(key)}`).join('\n');

            // Compute the secret key
            const secretKey = crypto.createHmac('sha256', 'WebAppData')
                .update(botToken)
                .digest();

            // Compute the final hash
            const calculatedHash = crypto.createHmac('sha256', secretKey)
                .update(dataCheckString)
                .digest('hex');

            // Validate the signature securely
            if (calculatedHash !== receivedHash) {
                console.error("Invalid initData signature.");
                throw new Error("Invalid initData signature");
            }

            // Also check for expiration (e.g., within the last 24 hours)
            const authDate = parseInt(parsedData.get('auth_date'), 10);
            const now = Math.floor(Date.now() / 1000);
            if (now - authDate > 86400) { // 24 hours
                throw new Error("initData is expired");
            }

            const userStr = parsedData.get('user');

            if (!userStr) {
                throw new Error("No user data found in initData");
            }

            userData = JSON.parse(userStr);
        }

        const userId = userData.id.toString();
        const username = userData.username || 'N/A';
        const firstName = userData.first_name || 'N/A';

        const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

        // Upsert user profile
        const updateResult = await collection.updateOne(
            { _id: userId },
            {
                $setOnInsert: {
                    balance: 50, // Welcome bonus matching Python bot
                    subscription_end: null,
                    referrals_count: 0,
                    used_configs: []
                },
                $set: {
                    username: username,
                    first_name: firstName,
                    last_login: new Date()
                }
            },
            { upsert: true }
        );

        return userId;
    } catch (e) {
        console.error("Auth error:", e);
        throw new Error("Authentication failed");
    }
};