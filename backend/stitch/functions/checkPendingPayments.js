exports = async function() {
    const userId = context.user.id;
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsColl = db.collection("payments");

    const pendingPayments = await paymentsColl.find({ user_id: userId, status: "pending" }).toArray();

    for (let i = 0; i < pendingPayments.length; i++) {
        await context.functions.execute("checkPayment", pendingPayments[i].payment_id);
    }

    return { success: true };
};
