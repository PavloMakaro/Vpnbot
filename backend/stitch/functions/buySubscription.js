exports = async function(periodKey) {
    const userId = context.user.identities[0].id;

    if (!userId) {
        return { success: false, error: "User ID not found in context" };
    }

    const SUBSCRIPTION_PERIODS = {
        '1_month': { price: 50, days: 30 },
        '2_months': { price: 90, days: 60 },
        '3_months': { price: 120, days: 90 }
    };

    if (!SUBSCRIPTION_PERIODS[periodKey]) {
        return { success: false, error: "Invalid subscription period" };
    }

    const price = SUBSCRIPTION_PERIODS[periodKey].price;
    const daysToAdd = SUBSCRIPTION_PERIODS[periodKey].days;

    const mongodb = context.services.get("mongodb-atlas");
    const usersColl = mongodb.db("vpn_bot").collection("users");
    const configsColl = mongodb.db("vpn_bot").collection("configs");

    // 1. Fetch user to check balance early
    let user = await usersColl.findOne({ _id: userId });
    if (!user) {
        return { success: false, error: "User not found" };
    }

    if (user.balance < price) {
        return { success: false, error: "Недостаточно средств на балансе" };
    }

    // 2. Reserve a config atomically
    // We update `used` from false to true to claim it
    const configDoc = await configsColl.findOneAndUpdate(
        { period: periodKey, used: false },
        { $set: { used: true, reserved_by: userId, reserved_at: new Date() } },
        { returnNewDocument: true }
    );

    if (!configDoc) {
        return { success: false, error: "Нет доступных конфигов для этого периода. Обратитесь в поддержку." };
    }

    // 3. Deduct balance and update subscription atomically
    try {
        // Calculate new subscription end date
        let currentEndStr = user.subscription_end;
        let newEnd;
        let now = new Date();

        if (currentEndStr) {
            let currentEnd = new Date(currentEndStr.replace(' ', 'T'));
            if (currentEnd > now) {
                // Add to existing
                newEnd = new Date(currentEnd.getTime() + daysToAdd * 24 * 60 * 60 * 1000);
            } else {
                // Start from now
                newEnd = new Date(now.getTime() + daysToAdd * 24 * 60 * 60 * 1000);
            }
        } else {
            // Start from now
            newEnd = new Date(now.getTime() + daysToAdd * 24 * 60 * 60 * 1000);
        }

        // Format to "YYYY-MM-DD HH:MM:SS" string to match legacy
        const formattedNewEnd = newEnd.toISOString().replace('T', ' ').substring(0, 19);

        // Build config history object
        const newUsedConfig = {
            config_name: configDoc.name,
            config_link: configDoc.link,
            config_code: configDoc.code,
            period: periodKey,
            issue_date: now.toISOString().replace('T', ' ').substring(0, 19),
            user_name: `${user.first_name} (@${user.username})`
        };

        const updateResult = await usersColl.updateOne(
            { _id: userId, balance: { $gte: price } },
            {
                $inc: { balance: -price },
                $set: { subscription_end: formattedNewEnd },
                $push: { used_configs: newUsedConfig }
            }
        );

        if (updateResult.modifiedCount === 0) {
            // Balance might have changed since we fetched it, release config
            await configsColl.updateOne({ _id: configDoc._id }, { $set: { used: false }, $unset: { reserved_by: "", reserved_at: "" } });
            return { success: false, error: "Не удалось списать средства" };
        }

        return {
            success: true,
            new_balance: user.balance - price,
            subscription_end: formattedNewEnd,
            config: configDoc
        };

    } catch (e) {
        // Release config on error
        await configsColl.updateOne({ _id: configDoc._id }, { $set: { used: false }, $unset: { reserved_by: "", reserved_at: "" } });
        console.error("Error updating user after reserving config:", e);
        return { success: false, error: "Ошибка при оформлении подписки" };
    }
};