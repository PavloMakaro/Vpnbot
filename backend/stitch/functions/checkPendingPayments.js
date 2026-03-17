exports = async function() {
    const userId = context.user.identities[0].id;
    if (!userId) {
        return { success: false, error: "User ID not found in context." };
    }

    const cluster = context.services.get("mongodb-atlas");
    const db = cluster.db("vpn_bot");
    const paymentsCol = db.collection("payments");
    const usersCol = db.collection("users");

    // Find all pending payments for user
    const pendingPayments = await paymentsCol.find({ user_id: userId, status: 'pending', method: 'yookassa_smart' }).toArray();

    if (pendingPayments.length === 0) {
        return { success: true, pending_count: 0, checked: 0, updated: 0 };
    }

    let updatedCount = 0;

    // Need to ask Yookassa for real time status
    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!shopId || !secretKey) {
        return { success: false, error: "Payment gateway configuration missing." };
    }

    const authString = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

    for (const payment of pendingPayments) {
        try {
            const response = await context.http.get({
                url: `https://api.yookassa.ru/v3/payments/${payment._id}`,
                headers: {
                    "Authorization": [`Basic ${authString}`],
                }
            });

            const responseBody = JSON.parse(response.body.text());

            if (responseBody.type === "error") {
                continue; // Skip errors on individual payments during bulk check
            }

            const status = responseBody.status;

            if (status === 'succeeded') {
                const amount = payment.amount;

                await usersCol.updateOne(
                    { _id: userId },
                    { $inc: { balance: amount } }
                );

                await paymentsCol.updateOne(
                    { _id: payment._id },
                    { $set: { status: 'confirmed' } }
                );
                updatedCount++;

            } else if (status === 'canceled') {
                await paymentsCol.updateOne(
                    { _id: payment._id },
                    { $set: { status: 'canceled' } }
                );
            }
        } catch (err) {
            console.error(`Error checking payment ${payment._id}: ${err}`);
        }
    }

    return {
        success: true,
        pending_count: pendingPayments.length,
        checked: pendingPayments.length,
        updated: updatedCount
    };
};
