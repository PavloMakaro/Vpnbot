exports = async function(loginPayload) {
    const crypto = require("crypto");
    const { initData, start_param } = loginPayload;

    if (!initData) {
        throw new Error("Missing initData");
    }

    const botToken = context.values.get("BOT_TOKEN");
    if (!botToken) {
        throw new Error("BOT_TOKEN is not configured in Context Values.");
    }

    // --- 1. VALIDATE INIT DATA ---
    const urlParams = new URLSearchParams(initData);
    const hash = urlParams.get('hash');
    urlParams.delete('hash');

    const dataCheckString = Array.from(urlParams.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, value]) => `${key}=${value}`)
        .join('\n');

    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
    const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

    if (calculatedHash !== hash) {
        throw new Error("Invalid initData hash");
    }

    // Extract user info
    const userStr = urlParams.get('user');
    if (!userStr) {
        throw new Error("No user data found in initData");
    }
    const userData = JSON.parse(decodeURIComponent(userStr));
    const userId = userData.id.toString();

    // --- 2. UPSERT USER & HANDLE REFERRALS ---
    const db = context.services.get("mongodb-atlas").db("vpn_bot_db");
    const usersCollection = db.collection("users");

    // Fetch existing user to check if they are new
    let userDoc = await usersCollection.findOne({ _id: userId });
    const isNewUser = !userDoc;

    let referredBy = null;
    let initialBalance = 0;

    // Referral constants matching Python legacy code
    const REFERRAL_BONUS_NEW_USER = 50;
    const REFERRAL_BONUS_REFERRER = 25;
    const REFERRAL_BONUS_DAYS = 7;

    if (isNewUser) {
        // Handle referral via start_param
        if (start_param && start_param !== userId) {
            const referrer = await usersCollection.findOne({ _id: start_param });
            if (referrer) {
                referredBy = start_param;
                initialBalance = REFERRAL_BONUS_NEW_USER;

                // Add days to referrer subscription
                let referrerSubEnd = referrer.subscription_end_date ? new Date(referrer.subscription_end_date) : new Date();
                if (referrerSubEnd < new Date()) {
                    referrerSubEnd = new Date();
                }
                referrerSubEnd.setDate(referrerSubEnd.getDate() + REFERRAL_BONUS_DAYS);

                // Update referrer
                await usersCollection.updateOne(
                    { _id: start_param },
                    {
                        $inc: { balance: REFERRAL_BONUS_REFERRER, referrals_count: 1 },
                        $set: { subscription_end_date: referrerSubEnd, subscription_end: referrerSubEnd.toISOString().replace('T', ' ').substring(0, 19) }
                    }
                );
                console.log(`Referrer ${start_param} updated for inviting ${userId}.`);
            }
        }

        // Initialize new user document
        userDoc = {
            _id: userId,
            username: userData.username || "",
            first_name: userData.first_name || "",
            balance: initialBalance,
            subscription_end: null,
            subscription_end_date: null,
            referred_by: referredBy,
            referrals_count: 0,
            used_configs: []
        };

        await usersCollection.insertOne(userDoc);
        console.log(`Created new user: ${userId}`);
    } else {
        // Update user's name/username if changed
        await usersCollection.updateOne(
            { _id: userId },
            {
                $set: {
                    username: userData.username || userDoc.username,
                    first_name: userData.first_name || userDoc.first_name
                }
            }
        );
        console.log(`Updated user data for: ${userId}`);
    }

    // --- 3. RETURN USER ID FOR CUSTOM AUTH ---
    // Realm custom auth expects a string user ID to be returned
    return userId;
};
