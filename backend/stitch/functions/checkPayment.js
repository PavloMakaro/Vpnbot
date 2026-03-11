exports = async function(paymentId) {
    const userId = context.user.id;

    if (!userId) {
        throw new Error("User not authenticated.");
    }

    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!shopId || !secretKey) {
        throw new Error("Server configuration error: Yookassa credentials missing.");
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    const paymentRecord = await paymentsCollection.findOne({ _id: paymentId, user_id: userId });

    if (!paymentRecord) {
        throw new Error("Payment not found or does not belong to user.");
    }

    if (paymentRecord.status === 'confirmed') {
        return { success: true, message: "Payment already confirmed." };
    }

    const base64Auth = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

    const properResponse = await context.http.get({
        url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
        headers: {
            "Authorization": [`Basic ${base64Auth}`]
        }
    });

    if (properResponse.statusCode !== 200) {
        throw new Error(`Yookassa API error: ${properResponse.body.text()}`);
    }

    const paymentData = JSON.parse(properResponse.body.text());

    if (paymentData.status === 'succeeded') {
        // Start a transaction to update both securely
        const session = context.services.get("mongodb-atlas").startSession();
        try {
            await session.withTransaction(async () => {
                await usersCollection.updateOne(
                    { _id: userId },
                    { $inc: { balance: paymentRecord.amount } },
                    { session }
                );

                await paymentsCollection.updateOne(
                    { _id: paymentId },
                    { $set: { status: 'confirmed' } },
                    { session }
                );
            });
            return { success: true, new_balance: true, amount: paymentRecord.amount };
        } finally {
            session.endSession();
        }
    } else if (paymentData.status === 'canceled') {
        await paymentsCollection.updateOne(
            { _id: paymentId },
            { $set: { status: 'canceled' } }
        );
        return { success: false, status: 'canceled' };
    }

    return { success: false, status: paymentData.status };
};
