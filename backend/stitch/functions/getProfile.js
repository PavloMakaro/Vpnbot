exports = async function() {
    const userId = context.user.identities[0].id;
    if (!userId) {
        throw new Error("User ID not found in context. identities[0].id is undefined.");
    }

    const cluster = context.services.get("mongodb-atlas");
    const db = cluster.db("vpn_bot");
    const users = db.collection("users");

    const user = await users.findOne({ _id: userId });

    if (!user) {
        throw new Error("User profile not found in database.");
    }

    return user;
};
