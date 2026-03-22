exports = async function(period) {
    const telegramId = context.user.identities[0].id.toString();
    if (!telegramId) {
        throw new Error("Unauthorized");
    }

    // Get valid subscription periods and prices
    const configPrices = {
        '1_month': { 'price': 50, 'days': 30 },
        '2_months': { 'price': 90, 'days': 60 },
        '3_months': { 'price': 120, 'days': 90 }
    };

    if (!configPrices[period]) {
        throw new Error("Invalid subscription period.");
    }

    const amount = configPrices[period].price;
    const days = configPrices[period].days;

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCollection = db.collection("users");
    const configsCollection = db.collection("configs");

    const user = await usersCollection.findOne({ _id: telegramId });
    if (!user) {
        throw new Error("User not found.");
    }

    if (user.balance < amount) {
        throw new Error(`Insufficient balance. Current balance: ${user.balance} RUB, required: ${amount} RUB.`);
    }

    // Atomically reserve a configuration to prevent race conditions
    const availableConfig = await configsCollection.findOneAndUpdate(
        { period: period, used: false },
        { $set: { used: true, assigned_to: telegramId, assigned_at: new Date() } },
        { returnNewDocument: true }
    );

    if (!availableConfig) {
        throw new Error("No available configurations for the selected period. Please try again later or contact support.");
    }

    // Calculate new subscription end date
    let newSubscriptionEnd;
    if (user.subscription_end && user.subscription_end > new Date()) {
        // Extend existing subscription
        newSubscriptionEnd = new Date(user.subscription_end);
        newSubscriptionEnd.setDate(newSubscriptionEnd.getDate() + days);
    } else {
        // Start new subscription
        newSubscriptionEnd = new Date();
        newSubscriptionEnd.setDate(newSubscriptionEnd.getDate() + days);
    }

    const configRecord = {
        config_name: availableConfig.name,
        config_link: availableConfig.link,
        config_code: availableConfig.code,
        period: period,
        issue_date: new Date().toISOString(),
        user_name: user.first_name || user.username || "User"
    };

    // Deduct balance, add config, and update subscription end date
    await usersCollection.updateOne(
        { _id: telegramId },
        {
            $inc: { balance: -amount },
            $set: { subscription_end: newSubscriptionEnd },
            $push: { used_configs: configRecord }
        }
    );

    return {
        success: true,
        message: "Subscription purchased successfully.",
        config: configRecord,
        newBalance: user.balance - amount,
        subscriptionEnd: newSubscriptionEnd
    };
};
