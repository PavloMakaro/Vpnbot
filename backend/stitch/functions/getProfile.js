exports = async function() {
    const userId = context.user.identities[0].id;
    if (!userId) {
        return { error: "User not authenticated" };
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const user = await db.collection("users").findOne({ _id: userId });

    if (!user) {
        return { error: "User profile not found" };
    }

    return {
        _id: user._id,
        balance: user.balance || 0,
        subscription_end: user.subscription_end || null,
        used_configs: user.used_configs || [],
        username: user.username || "",
        first_name: user.first_name || ""
    };
};