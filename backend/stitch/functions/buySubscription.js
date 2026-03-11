exports = async function(periodKey) {
    const userId = context.user.id;

    if (!userId) {
        throw new Error("User not authenticated.");
    }

    const SUBSCRIPTION_PERIODS = {
        '1_month': { price: 50, days: 30 },
        '2_months': { price: 90, days: 60 },
        '3_months': { price: 120, days: 90 }
    };

    if (!SUBSCRIPTION_PERIODS[periodKey]) {
        throw new Error("Invalid subscription period.");
    }

    const subData = SUBSCRIPTION_PERIODS[periodKey];
    const amount = subData.price;
    const daysToAdd = subData.days;

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCollection = db.collection("users");
    const configsCollection = db.collection("configs");

    // Start a transaction for safe processing (requires Atlas cluster to be replica set, true for Atlas)
    const session = context.services.get("mongodb-atlas").startSession();

    try {
        let result;
        await session.withTransaction(async () => {
            const user = await usersCollection.findOne({ _id: userId }, { session });

            if (!user) {
                throw new Error("User not found.");
            }

            if ((user.balance || 0) < amount) {
                throw new Error("Insufficient balance.");
            }

            // Atomically reserve a config
            // Note: MongoDB Atlas App Services serverless functions might not support full multi-document transactions easily
            // without a dedicated cluster. We'll use findOneAndUpdate for atomicity on configs.
            const config = await configsCollection.findOneAndUpdate(
                { period: periodKey, used: false },
                { $set: { used: true } },
                { session, returnNewDocument: true }
            );

            if (!config) {
                throw new Error("No available configs for this period. Please contact support.");
            }

            // Calculate new end date
            let currentEnd = user.subscription_end;
            let now = new Date();
            let endDate = now;

            if (currentEnd) {
                // parse python string 'YYYY-MM-DD HH:MM:SS' if it is string
                if (typeof currentEnd === 'string') {
                    currentEnd = new Date(currentEnd.replace(" ", "T"));
                }
                if (currentEnd > now) {
                    endDate = currentEnd;
                }
            }

            endDate.setDate(endDate.getDate() + daysToAdd);

            // Format issue_date like python legacy
            const pad = (n) => n < 10 ? '0' + n : n;
            const issueDateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

            const usedConfig = {
                config_name: config.name,
                config_link: config.link,
                config_code: config.code,
                period: periodKey,
                issue_date: issueDateStr,
                user_name: `${user.first_name} (@${user.username})`
            };

            // Deduct balance, update subscription_end, push to used_configs
            await usersCollection.updateOne(
                { _id: userId },
                {
                    $inc: { balance: -amount },
                    $set: { subscription_end: endDate },
                    $push: { used_configs: usedConfig }
                },
                { session }
            );

            result = { success: true, config: usedConfig, new_balance: user.balance - amount, end_date: endDate };
        });

        return result;

    } catch (e) {
        return { success: false, error: e.message };
    } finally {
        session.endSession();
    }
};
