exports = async function() {
    const userId = context.user.id;

    if (!userId) {
        return { success: false, message: "User not authenticated." };
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCollection = db.collection("payments");

    // Get all pending balance topups for this user
    const pendingPayments = await paymentsCollection.find({
        user_id: userId,
        status: 'pending',
        type: 'balance_topup'
    }).toArray();

    if (pendingPayments.length === 0) {
        return { success: true, count: 0, updated: 0 };
    }

    let updatedCount = 0;

    // We can reuse the checkPayment function we already wrote
    // but calling other functions from a function in Stitch is context.functions.execute("checkPayment", id)
    for (const payment of pendingPayments) {
        try {
            const result = await context.functions.execute("checkPayment", payment._id);
            if (result && result.success && result.new_balance) {
                updatedCount++;
            }
        } catch (e) {
            console.error(`Error checking payment ${payment._id}: ${e.message}`);
        }
    }

    return { success: true, count: pendingPayments.length, updated: updatedCount };
};
