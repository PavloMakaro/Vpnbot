exports = async function() {
    const userId = context.user.id; // From Realm Auth

    if (!userId) {
        throw new Error("User not authenticated.");
    }

    const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

    const userProfile = await collection.findOne({ _id: userId });

    if (!userProfile) {
        throw new Error("User profile not found in database.");
    }

    // Calculate days left
    let daysLeft = 0;
    if (userProfile.subscription_end) {
        const endStr = typeof userProfile.subscription_end === 'string'
            ? userProfile.subscription_end
            : userProfile.subscription_end.toISOString();
        const endDate = new Date(endStr.replace(" ", "T")); // handle Python datetimes
        const now = new Date();
        if (endDate > now) {
            daysLeft = Math.floor((endDate - now) / (1000 * 60 * 60 * 24));
        }
    }

    return {
        id: userProfile._id,
        username: userProfile.username,
        first_name: userProfile.first_name,
        balance: userProfile.balance || 0,
        subscription_end: userProfile.subscription_end,
        days_left: daysLeft,
        used_configs: userProfile.used_configs || [],
        referrals_count: userProfile.referrals_count || 0
    };
};
