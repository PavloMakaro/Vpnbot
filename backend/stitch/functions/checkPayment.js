exports = async function(paymentId) {
    const userId = context.user.identities[0].id;
    if (!userId) {
        return { success: false, error: "User ID not found in context." };
    }

    const cluster = context.services.get("mongodb-atlas");
    const db = cluster.db("vpn_bot");
    const paymentsCol = db.collection("payments");
    const usersCol = db.collection("users");

    // Check local database first for state
    const payment = await paymentsCol.findOne({ _id: paymentId, user_id: userId });

    if (!payment) {
        return { success: false, error: "Payment not found or belongs to someone else." };
    }

    // If it's already finalized in DB, just return that state to avoid unnecessary HTTP calls
    if (payment.status !== 'pending') {
         return {
            success: true,
            status: payment.status,
            amount: payment.amount,
            message: `Payment previously marked as ${payment.status}.`
        };
    }

    // Need to ask Yookassa for real time status
    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!shopId || !secretKey) {
        return { success: false, error: "Payment gateway configuration missing." };
    }

    const authString = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

    try {
        const response = await context.http.get({
            url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
            headers: {
                "Authorization": [`Basic ${authString}`],
            }
        });

        const responseBody = JSON.parse(response.body.text());

        if (responseBody.type === "error") {
            return { success: false, error: responseBody.description };
        }

        const status = responseBody.status;

        // Match Python backend logic
        if (status === 'succeeded') {
            const amount = payment.amount;

            // Atomically update balance
            await usersCol.updateOne(
                { _id: userId },
                { $inc: { balance: amount } }
            );

            // Mark payment as confirmed
            await paymentsCol.updateOne(
                { _id: paymentId },
                { $set: { status: 'confirmed' } }
            );

            return { success: true, status: 'succeeded', amount: amount, message: "Balance updated successfully!" };

        } else if (status === 'canceled') {
            await paymentsCol.updateOne(
                { _id: paymentId },
                { $set: { status: 'canceled' } }
            );

            return { success: true, status: 'canceled', message: "Payment was canceled." };
        }

        return { success: true, status: status, message: "Payment is still pending." };

    } catch (err) {
        return { success: false, error: err.message };
    }
};
