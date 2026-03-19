exports = async function() {
    const mongodb = context.services.get("mongodb-atlas");
    const usersCollection = mongodb.db("vpn_bot").collection("users");

    // Extract Telegram ID from context
    const userId = context.user.identities[0].id;

    if (!userId) {
        throw new Error("User ID not found in context. identities");
    }

    const userProfile = await usersCollection.findOne({ _id: userId });

    if (!userProfile) {
        throw new Error(`Profile not found for ID: ${userId}`);
    }

    return userProfile;
};