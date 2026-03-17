exports = async function(period) {
    const userId = context.user.identities[0].id;
    if (!userId) {
        return { success: false, error: "User ID not found in context." };
    }

    // Validate period
    const SUBSCRIPTION_PERIODS = {
        '1_month': { price: 50, days: 30 },
        '2_months': { price: 90, days: 60 },
        '3_months': { price: 120, days: 90 }
    };

    if (!SUBSCRIPTION_PERIODS[period]) {
        return { success: false, error: "Invalid subscription period." };
    }

    const amount = SUBSCRIPTION_PERIODS[period].price;
    const addDays = SUBSCRIPTION_PERIODS[period].days;

    const cluster = context.services.get("mongodb-atlas");
    const db = cluster.db("vpn_bot");
    const usersCol = db.collection("users");
    const configsCol = db.collection("configs");

    // Start transaction if supported or simply do atomic operations
    // First, check user balance
    const user = await usersCol.findOne({ _id: userId });
    if (!user) {
        return { success: false, error: "User not found." };
    }

    const balance = user.balance || 0;
    if (balance < amount) {
        return { success: false, error: `Insufficient balance. Required: ${amount}, Available: ${balance}` };
    }

    // Atomically find an available config and mark it as used
    const config = await configsCol.findOneAndUpdate(
        { period: period, used: false },
        { $set: { used: true } },
        { returnNewDocument: true }
    );

    if (!config) {
        return { success: false, error: "No available configurations for this period. Please contact support." };
    }

    // Update user: deduct balance, extend subscription, append to used_configs
    const currentEnd = user.subscription_end ? new Date(user.subscription_end) : new Date();
    // If subscription already expired, start from now
    const startDate = currentEnd < new Date() ? new Date() : currentEnd;

    const newEnd = new Date(startDate.getTime());
    newEnd.setDate(newEnd.getDate() + addDays);

    // Format to YYYY-MM-DD HH:MM:SS matching python legacy format for now, or just save Date object
    const newEndStr = newEnd.toISOString().slice(0, 19).replace('T', ' ');

    const usedConfigEntry = {
        config_name: config.name,
        config_link: config.link,
        config_code: config.code || "",
        period: period,
        issue_date: new Date().toISOString().slice(0, 19).replace('T', ' '),
        user_name: `${user.first_name || 'N/A'} (@${user.username || 'N/A'})`
    };

    const updateResult = await usersCol.updateOne(
        { _id: userId, balance: { $gte: amount } }, // double check balance hasn't dropped
        {
            $inc: { balance: -amount },
            $set: { subscription_end: newEndStr },
            $push: { used_configs: usedConfigEntry }
        }
    );

    if (updateResult.modifiedCount === 0) {
        // Balance check failed or user disappeared. Revert config reservation.
        await configsCol.updateOne({ _id: config._id }, { $set: { used: false } });
        return { success: false, error: "Failed to deduct balance. Operation cancelled." };
    }

    return {
        success: true,
        message: "Subscription purchased successfully.",
        new_balance: balance - amount,
        subscription_end: newEndStr,
        config: {
            link: config.link,
            code: config.code || ""
        }
    };
};
