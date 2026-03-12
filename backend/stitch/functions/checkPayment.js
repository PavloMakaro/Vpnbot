exports = async function(paymentId) {
    const userId = context.user.id;
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    try {
        const paymentRecord = await paymentsCollection.findOne({ _id: paymentId, user_id: userId });

        if (!paymentRecord) {
            return { error: "Payment not found" };
        }

        if (paymentRecord.status === "confirmed") {
            return { status: "succeeded", alreadyConfirmed: true };
        }

        if (paymentRecord.status === "canceled" || paymentRecord.status === "rejected") {
            return { status: "canceled" };
        }

        const shopId = context.values.get("YOOKASSA_SHOP_ID");
        const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

        const url = `https://api.yookassa.ru/v3/payments/${paymentId}`;
        const authHeader = "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64");

        const response = await context.http.get({
            url: url,
            headers: {
                "Authorization": [authHeader]
            }
        });

        const responseData = JSON.parse(response.body.text());

        if (responseData.type === "error") {
            console.error("Yookassa check payment error:", responseData);
            return { error: "Failed to verify payment status" };
        }

        const status = responseData.status;

        if (status === "succeeded") {
            // Atomically update the payment record and balance
            const session = db.getMongo().startSession();
            try {
                session.startTransaction();

                const updatePaymentResult = await paymentsCollection.updateOne(
                    { _id: paymentId, status: "pending" },
                    { $set: { status: "confirmed", confirmed_at: new Date() } }
                );

                if (updatePaymentResult.modifiedCount > 0) {
                    await usersCollection.updateOne(
                        { _id: userId },
                        { $inc: { balance: paymentRecord.amount } }
                    );
                }

                await session.commitTransaction();
                return { status: "succeeded", amount: paymentRecord.amount };

            } catch (txError) {
                await session.abortTransaction();
                console.error("Transaction error updating payment:", txError);
                return { error: "Failed to update balance" };
            } finally {
                session.endSession();
            }
        } else if (status === "canceled") {
            await paymentsCollection.updateOne(
                { _id: paymentId },
                { $set: { status: "canceled", updated_at: new Date() } }
            );
            return { status: "canceled" };
        }

        return { status: "pending" };

    } catch (e) {
        console.error("Check payment error:", e);
        return { error: "Internal error checking payment" };
    }
};