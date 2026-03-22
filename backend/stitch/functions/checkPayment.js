exports = async function(paymentId) {
    const telegramId = context.user.identities[0].id.toString();
    if (!telegramId) {
        throw new Error("Unauthorized");
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    // Yookassa Integration
    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!shopId || !secretKey) {
        throw new Error("Yookassa credentials not configured.");
    }

    const paymentRecord = await paymentsCollection.findOne({ _id: paymentId, user_id: telegramId });
    if (!paymentRecord) {
        throw new Error("Payment not found or does not belong to you.");
    }

    if (paymentRecord.status === "succeeded" || paymentRecord.status === "confirmed") {
        return { success: true, message: "Payment already confirmed." };
    }

    const response = await context.http.get({
        url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
        headers: {
            "Authorization": ["Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64")]
        }
    });

    if (response.statusCode >= 400) {
        throw new Error(`Yookassa API error: ${response.body.text()}`);
    }

    const paymentInfo = JSON.parse(response.body.text());

    if (paymentInfo.status === "succeeded") {
        await paymentsCollection.updateOne(
            { _id: paymentId },
            { $set: { status: "confirmed", confirmed_at: new Date() } }
        );

        await usersCollection.updateOne(
            { _id: telegramId },
            { $inc: { balance: paymentRecord.amount } }
        );

        return { success: true, message: "Payment confirmed and balance updated." };
    } else if (paymentInfo.status === "canceled") {
        await paymentsCollection.updateOne(
            { _id: paymentId },
            { $set: { status: "canceled", canceled_at: new Date() } }
        );
        return { success: false, message: "Payment was canceled." };
    } else {
        return { success: false, message: "Payment is still pending." };
    }
};
