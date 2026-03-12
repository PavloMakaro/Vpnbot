exports = async function(period) {
    const userId = context.user.id;

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCollection = db.collection("users");
    const configsCollection = db.collection("configs");

    const subscriptionPeriods = {
        '1_month': { price: 50, days: 30 },
        '2_months': { price: 90, days: 60 },
        '3_months': { price: 120, days: 90 }
    };

    if (!subscriptionPeriods[period]) {
        return { success: false, error: "Invalid subscription period" };
    }

    const amount = subscriptionPeriods[period].price;
    const daysToAdd = subscriptionPeriods[period].days;

    try {
        // Step 1: Check balance
        const userProfile = await usersCollection.findOne({ _id: userId });

        if (!userProfile) {
            return { success: false, error: "User not found" };
        }

        if (userProfile.balance < amount) {
            return {
                success: false,
                error: `Недостаточно средств. Ваш баланс: ${userProfile.balance} ₽. Требуется: ${amount} ₽.`
            };
        }

        // Step 2: Atomically reserve a config
        const reservedConfig = await configsCollection.findOneAndUpdate(
            { period: period, used: false },
            { $set: { used: true } },
            { returnNewDocument: true }
        );

        if (!reservedConfig) {
            return { success: false, error: "Извините, сейчас нет доступных конфигов для этого периода." };
        }

        // Step 3: Deduct balance and update subscription
        let currentEnd = new Date();
        if (userProfile.subscription_end) {
            currentEnd = new Date(userProfile.subscription_end);
            if (currentEnd < new Date()) {
                currentEnd = new Date(); // If expired, start from now
            }
        }

        // Add days
        const newEnd = new Date(currentEnd);
        newEnd.setDate(newEnd.getDate() + daysToAdd);

        // Create config log
        const configLog = {
            config_name: reservedConfig.name,
            config_link: reservedConfig.link,
            config_code: reservedConfig.code,
            period: period,
            issue_date: new Date(),
            user_name: `${userProfile.first_name} (@${userProfile.username || ''})`
        };

        // Deduct balance and append config
        await usersCollection.updateOne(
            { _id: userId },
            {
                $inc: { balance: -amount },
                $set: { subscription_end: newEnd },
                $push: { used_configs: configLog }
            }
        );

        return {
            success: true,
            config: configLog,
            new_balance: userProfile.balance - amount,
            subscription_end: newEnd
        };
    } catch (e) {
        console.error("Buy subscription error:", e);
        return { success: false, error: "Произошла ошибка при покупке подписки." };
    }
};