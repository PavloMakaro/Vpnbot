exports = async function(periodKey) {
    const userId = context.user.identities[0].id;
    if (!userId) {
        throw new Error("User not authenticated.");
    }

    // Hardcoded prices and periods matching Python implementation
    const SUBSCRIPTION_PERIODS = {
        '1_month': { price: 50, days: 30 },
        '2_months': { price: 90, days: 60 },
        '3_months': { price: 120, days: 90 }
    };

    if (!SUBSCRIPTION_PERIODS[periodKey]) {
        throw new Error("Invalid period.");
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCol = db.collection("users");
    const configsCol = db.collection("configs");

    const user = await usersCol.findOne({ telegram_id: userId });
    if (!user) {
        throw new Error("User profile not found.");
    }

    const price = SUBSCRIPTION_PERIODS[periodKey].price;
    if (user.balance < price) {
        throw new Error("Insufficient balance.");
    }

    // Atomically reserve configuration
    const config = await configsCol.findOneAndUpdate(
        { period: periodKey, used: false },
        { $set: { used: true } },
        { returnNewDocument: true }
    );

    if (!config) {
        throw new Error("No available configurations for this period.");
    }

    // Deduct balance and update subscription
    const currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
    const addDays = SUBSCRIPTION_PERIODS[periodKey].days;
    const newEnd = new Date(currentEnd.getTime() + addDays * 24 * 60 * 60 * 1000);

    const issueDate = new Date();

    const usedConfig = {
        config_name: config.name,
        config_link: config.link,
        period: periodKey,
        issue_date: issueDate
    };

    await usersCol.updateOne(
        { telegram_id: userId },
        {
            $inc: { balance: -price },
            $set: { subscription_end: newEnd },
            $push: { used_configs: usedConfig }
        }
    );

    return { success: true, newEnd: newEnd, config: usedConfig };
};