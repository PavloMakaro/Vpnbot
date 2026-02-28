exports = async function() {
    const userId = context.user.id; // Atlas App Services specific user id
    if (!userId) {
        throw new Error("User is not authenticated.");
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot_db");
    const usersCollection = db.collection("users");

    // Fetch the user document
    const userDoc = await usersCollection.findOne({ _id: userId });

    if (!userDoc) {
        throw new Error("User profile not found.");
    }

    // Calculate days left for subscription
    let daysLeft = 0;
    if (userDoc.subscription_end_date) {
        const now = new Date();
        const end = new Date(userDoc.subscription_end_date);
        if (end > now) {
            const diffTime = Math.abs(end - now);
            daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        }
    }

    // Format the date if it exists
    let subscriptionEndDateFormatted = "Нет активной подписки";
    if (daysLeft > 0 && userDoc.subscription_end_date) {
        const d = new Date(userDoc.subscription_end_date);
        const day = d.getDate().toString().padStart(2, '0');
        const month = (d.getMonth() + 1).toString().padStart(2, '0');
        const year = d.getFullYear();
        subscriptionEndDateFormatted = `${day}.${month}.${year}`;
    }

    // Structure response for the frontend
    return {
        id: userDoc._id,
        first_name: userDoc.first_name,
        username: userDoc.username,
        balance: userDoc.balance || 0,
        referrals_count: userDoc.referrals_count || 0,
        daysLeft: daysLeft,
        subscriptionEndDateFormatted: subscriptionEndDateFormatted,
        used_configs: userDoc.used_configs || []
    };
};