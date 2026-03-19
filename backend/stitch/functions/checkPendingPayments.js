exports = async function() {
    const userId = context.user.identities[0].id;

    if (!userId) {
        return { success: false, error: "User ID not found in context" };
    }

    const mongodb = context.services.get("mongodb-atlas");
    const paymentsColl = mongodb.db("vpn_bot").collection("payments");

    const pendingPayments = await paymentsColl.find({ user_id: userId, status: "pending" }).toArray();

    let processedCount = 0;

    for (const payment of pendingPayments) {
        try {
            const checkResult = await context.functions.execute("checkPayment", payment._id);
            if (checkResult && checkResult.status === "confirmed") {
                processedCount++;
            }
        } catch (e) {
            console.error("Error processing pending payment:", payment._id, e);
        }
    }

    return { success: true, processed_count: processedCount };
};