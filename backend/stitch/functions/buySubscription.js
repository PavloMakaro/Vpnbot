exports = async function(periodKey) {
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersColl = db.collection("users");
    const configsColl = db.collection("configs");

    const prices = context.functions.execute("getConfigs");
    if (!prices[periodKey]) {
        return { success: false, message: "Invalid subscription period." };
    }

    const cost = prices[periodKey].price;
    const days = prices[periodKey].days;
    const userId = context.user.id;

    // Check balance first
    const user = await usersColl.findOne({ _id: userId });
    if (!user) {
        return { success: false, message: "User not found." };
    }

    if ((user.balance || 0) < cost) {
        return { success: false, message: "Insufficient balance." };
    }

    // Atomically reserve a config
    const config = await configsColl.findOneAndUpdate(
        { period: periodKey, used: false },
        { $set: { used: true } },
        { returnNewDocument: true }
    );

    if (!config) {
        return { success: false, message: "No available configurations for this period." };
    }

    // Calculate new subscription end
    let currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
    if (isNaN(currentEnd)) currentEnd = new Date();
    const now = new Date();
    if (currentEnd < now) currentEnd = now;

    currentEnd.setDate(currentEnd.getDate() + days);

    // Format date roughly as YYYY-MM-DD HH:MM:SS for compatibility if needed, but Date object is better in Mongo.
    // Keeping as string if memory/legacy script used string, but native Date is preferred.
    // Legacy python script uses string formatted as YYYY-MM-DD HH:MM:SS, let's keep string for compatibility or use Date if new.
    // Let's use Date objects for easier math in JS and update Python to handle Date.
    // Memory says: migrate_to_mongo script handles migration. So we can use strings if we want.
    // Let's stick to the Python format string.
    const pad = (n) => n.toString().padStart(2, '0');
    const newEndStr = `${currentEnd.getFullYear()}-${pad(currentEnd.getMonth()+1)}-${pad(currentEnd.getDate())} ${pad(currentEnd.getHours())}:${pad(currentEnd.getMinutes())}:${pad(currentEnd.getSeconds())}`;


    const usedConfigEntry = {
        config_name: config.name,
        config_link: config.link,
        config_code: config.code,
        period: periodKey,
        issue_date: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user_name: `${user.first_name || ""} (@${user.username || ""})`.trim()
    };

    // Deduct balance, add config, update sub date
    const result = await usersColl.updateOne(
        { _id: userId, balance: { $gte: cost } }, // Ensure balance hasn't changed below cost
        {
            $inc: { balance: -cost },
            $set: { subscription_end: newEndStr },
            $push: { used_configs: usedConfigEntry }
        }
    );

    if (result.modifiedCount === 0) {
        // Rollback config reservation if user update failed
        await configsColl.updateOne({ _id: config._id }, { $set: { used: false } });
        return { success: false, message: "Failed to update user profile." };
    }

    return { success: true, message: "Subscription purchased successfully.", config: config, new_end: newEndStr };
};
