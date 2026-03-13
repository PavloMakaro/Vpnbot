exports = async function() {
    const userId = context.user.id;
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersColl = db.collection("users");

    const user = await usersColl.findOne({ _id: userId });
    if (!user) {
        throw new Error("User not found");
    }
    return user;
};
