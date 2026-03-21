exports = async function() {
    const userId = context.user.identities[0].id;
    if (!userId) {
        throw new Error("User not authenticated.");
    }

    const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
    const profile = await collection.findOne({ telegram_id: userId });

    return profile;
};