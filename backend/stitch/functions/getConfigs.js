exports = async function() {
    const userId = context.user.id;

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCollection = db.collection("users");
    const configsCollection = db.collection("configs");

    try {
        const userProfile = await usersCollection.findOne({ _id: userId });

        if (!userProfile) {
            return { error: "User not found" };
        }

        const usedConfigs = userProfile.used_configs || [];

        // Find available counts per period
        const availableCounts = {};
        const periods = ['1_month', '2_months', '3_months'];

        for (const period of periods) {
            const count = await configsCollection.count({ period: period, used: false });
            availableCounts[period] = count;
        }

        return {
            used_configs: usedConfigs,
            available_counts: availableCounts,
            subscription_periods: {
                '1_month': { price: 50, days: 30 },
                '2_months': { price: 90, days: 60 },
                '3_months': { price: 120, days: 90 }
            }
        };
    } catch (e) {
        console.error("Get configs error:", e);
        return { error: "Failed to get configs" };
    }
};