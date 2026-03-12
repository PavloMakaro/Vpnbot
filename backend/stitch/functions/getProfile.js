exports = async function() {
    const userId = context.user.id;

    const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

    try {
        const userProfile = await collection.findOne({ _id: userId });

        if (!userProfile) {
            return { error: "User not found" };
        }

        // Calculate days left
        let daysLeft = 0;
        let subscriptionStatus = "Нет активной подписки";

        if (userProfile.subscription_end) {
            const endDate = new Date(userProfile.subscription_end);
            const now = new Date();

            if (endDate > now) {
                const diffTime = Math.abs(endDate - now);
                daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                // Format date manually instead of toLocaleDateString which might not be supported in Stitch
                const day = endDate.getDate().toString().padStart(2, '0');
                const month = (endDate.getMonth() + 1).toString().padStart(2, '0');
                const year = endDate.getFullYear();

                subscriptionStatus = `Активна еще ${daysLeft} дней (до ${day}.${month}.${year})`;
            } else {
                daysLeft = 0;
            }
        }

        return {
            id: userProfile._id,
            first_name: userProfile.first_name,
            username: userProfile.username,
            balance: userProfile.balance || 0,
            subscription_end: userProfile.subscription_end,
            days_left: daysLeft,
            subscription_status: subscriptionStatus,
            referrals_count: userProfile.referrals_count || 0
        };
    } catch (e) {
        console.error("Get profile error:", e);
        return { error: "Failed to get profile" };
    }
};