exports = async function() {
    const userId = context.user.identities[0].id;
    if (!userId) {
        throw new Error("User not authenticated.");
    }

    // Hardcoded prices and periods matching Python implementation
    const SUBSCRIPTION_PERIODS = {
        '1_month': { price: 50, days: 30, title: "1 month" },
        '2_months': { price: 90, days: 60, title: "2 months" },
        '3_months': { price: 120, days: 90, title: "3 months" }
    };

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const configsCol = db.collection("configs");

    const availability = {};
    for (const key in SUBSCRIPTION_PERIODS) {
        const count = await configsCol.count({ period: key, used: false });
        availability[key] = {
            ...SUBSCRIPTION_PERIODS[key],
            available: count > 0
        };
    }

    return availability;
};