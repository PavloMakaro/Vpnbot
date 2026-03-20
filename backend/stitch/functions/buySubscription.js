exports = async function(periodKey) {
    const userId = context.user.identities[0].id;
    if (!userId) {
        return { error: "User not authenticated" };
    }

    const SUBSCRIPTION_PERIODS = {
        '1_month': { price: 50, days: 30 },
        '2_months': { price: 90, days: 60 },
        '3_months': { price: 120, days: 90 }
    };

    if (!SUBSCRIPTION_PERIODS[periodKey]) {
        return { error: "Invalid subscription period" };
    }

    const { price, days } = SUBSCRIPTION_PERIODS[periodKey];

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCollection = db.collection("users");
    const configsCollection = db.collection("configs");

    // Check balance first
    const user = await usersCollection.findOne({ _id: userId });
    if (!user) {
        return { error: "User not found" };
    }

    if ((user.balance || 0) < price) {
        return { error: `Insufficient balance. Required: ${price} ₽` };
    }

    // Step 1: Atomically reserve an available configuration for this period
    const config = await configsCollection.findOneAndUpdate(
        { period: periodKey, used: false },
        { $set: { used: true } },
        { returnNewDocument: true }
    );

    if (!config) {
        return { error: "No available configs for this period. Please contact support." };
    }

    // Step 2: Deduct balance and update subscription in user profile

    // Calculate new expiration date
    let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
    if (isNaN(currentEnd.getTime()) || currentEnd < new Date()) {
        currentEnd = new Date();
    }

    currentEnd.setDate(currentEnd.getDate() + days);

    // Format to match legacy "YYYY-MM-DD HH:MM:SS" string format
    const pad = (n) => n.toString().padStart(2, '0');
    const newEndStr = `${currentEnd.getFullYear()}-${pad(currentEnd.getMonth() + 1)}-${pad(currentEnd.getDate())} ${pad(currentEnd.getHours())}:${pad(currentEnd.getMinutes())}:${pad(currentEnd.getSeconds())}`;

    // Record used config
    const usedConfigRecord = {
        config_name: config.name,
        config_link: config.link,
        config_code: config.code || "",
        period: periodKey,
        issue_date: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user_name: user.first_name || user.username || "User"
    };

    const updateResult = await usersCollection.updateOne(
        { _id: userId, balance: { $gte: price } }, // Double check balance to prevent race conditions
        {
            $inc: { balance: -price },
            $set: { subscription_end: newEndStr },
            $push: { used_configs: usedConfigRecord }
        }
    );

    if (updateResult.modifiedCount === 0) {
        // Fallback: Restore the configuration if user update fails (e.g. balance changed concurrently)
        await configsCollection.updateOne({ _id: config._id }, { $set: { used: false } });
        return { error: "Purchase failed due to concurrent modification. Config restored." };
    }

    return {
        success: true,
        config: config,
        new_balance: user.balance - price,
        subscription_end: newEndStr
    };
};