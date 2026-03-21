exports = async function(paymentId) {
    const userId = context.user.identities[0].id;
    if (!userId) {
        throw new Error("User not authenticated.");
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCol = db.collection("payments");
    const usersCol = db.collection("users");

    const paymentRecord = await paymentsCol.findOne({ payment_id: paymentId, user_id: userId });
    if (!paymentRecord) {
        throw new Error("Payment record not found.");
    }

    if (paymentRecord.status !== "pending") {
        return paymentRecord;
    }

    const yookassaShopId = context.values.get("YOOKASSA_SHOP_ID");
    const yookassaSecretKey = context.values.get("YOOKASSA_SECRET_KEY");

    const response = await context.http.get({
        url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
        headers: {
            "Authorization": [`Basic ${Buffer.from(yookassaShopId + ":" + yookassaSecretKey).toString("base64")}`]
        }
    });

    if (response.statusCode >= 200 && response.statusCode < 300) {
        const paymentData = JSON.parse(response.body.text());

        if (paymentData.status === "succeeded") {
            await usersCol.updateOne(
                { telegram_id: userId },
                { $inc: { balance: paymentRecord.amount } }
            );

            await paymentsCol.updateOne(
                { payment_id: paymentId },
                { $set: { status: "confirmed" } }
            );

            return { success: true, newStatus: "confirmed" };
        } else if (paymentData.status === "canceled") {
            await paymentsCol.updateOne(
                { payment_id: paymentId },
                { $set: { status: "canceled" } }
            );

            return { success: true, newStatus: "canceled" };
        }

        return { success: true, newStatus: "pending" };
    } else {
        throw new Error(`Failed to check payment: ${response.body.text()}`);
    }
};