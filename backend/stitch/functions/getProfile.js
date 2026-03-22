exports = async function() {
    const userId = context.user.identities[0].id;
    if (!userId) {
        throw new Error("User ID not found in context. identities missing");
    }

    const telegramId = userId.toString();

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCollection = db.collection("users");

    const user = await usersCollection.findOne({ _id: telegramId });
    if (!user) {
        throw new Error("User not found");
    }

    return user;
};
