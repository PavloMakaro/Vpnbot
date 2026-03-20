exports = async function(paymentId) {
    const userId = context.user.identities[0].id;
    if (!userId) {
        return { error: "User not authenticated" };
    }

    if (!paymentId) {
        return { error: "Missing payment ID" };
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    // Fetch the payment
    const paymentRecord = await paymentsCollection.findOne({ _id: paymentId, user_id: userId });
    if (!paymentRecord) {
        return { error: "Payment not found or does not belong to user" };
    }

    if (paymentRecord.status !== "pending") {
        return { status: paymentRecord.status, message: "Payment already processed" };
    }

    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");
    const authHeader = "Basic " + Buffer.from(shopId + ":" + secretKey).toString("base64");

    try {
        const response = await context.http.get({
            url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
            headers: {
                "Authorization": [authHeader]
            }
        });

        if (response.statusCode >= 400) {
            console.error("Yookassa error: ", response.body.text());
            return { error: "Failed to fetch payment status from Yookassa" };
        }

        const yookassaPayment = EJSON.parse(response.body.text());
        const status = yookassaPayment.status;

        if (status === 'succeeded') {
            // Important: Atomic update of payment to prevent double processing
            const updateResult = await paymentsCollection.updateOne(
                { _id: paymentId, status: "pending" },
                { $set: { status: "confirmed" } }
            );

            if (updateResult.modifiedCount > 0) {
                // Update user balance
                await usersCollection.updateOne(
                    { _id: userId },
                    { $inc: { balance: paymentRecord.amount } }
                );
                return { status: "succeeded", message: "Balance updated successfully" };
            } else {
                 return { status: "confirmed", message: "Payment already processed concurrently" };
            }
        } else if (status === 'canceled') {
            await paymentsCollection.updateOne(
                { _id: paymentId },
                { $set: { status: "canceled" } }
            );
            return { status: "canceled", message: "Payment was canceled" };
        }

        // Still pending
        return { status: "pending", message: "Payment is still pending" };

    } catch (e) {
        console.error("Error checking payment:", e);
        return { error: "Internal payment check error." };
    }
};