exports = async function() {
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    // Yookassa Integration
    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!shopId || !secretKey) {
        throw new Error("Yookassa credentials not configured.");
    }

    const pendingPayments = await paymentsCollection.find({ status: "pending", method: "yookassa_smart" }).toArray();

    const results = [];

    for (const paymentRecord of pendingPayments) {
        const paymentId = paymentRecord._id;
        const telegramId = paymentRecord.user_id;

        try {
            const response = await context.http.get({
                url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
                headers: {
                    "Authorization": ["Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64")]
                }
            });

            if (response.statusCode >= 400) {
                results.push({ paymentId: paymentId, error: `API error: ${response.statusCode}` });
                continue;
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

                results.push({ paymentId: paymentId, status: "confirmed", user: telegramId, amount: paymentRecord.amount });
            } else if (paymentInfo.status === "canceled") {
                await paymentsCollection.updateOne(
                    { _id: paymentId },
                    { $set: { status: "canceled", canceled_at: new Date() } }
                );
                results.push({ paymentId: paymentId, status: "canceled" });
            } else {
                results.push({ paymentId: paymentId, status: paymentInfo.status });
            }
        } catch (e) {
            results.push({ paymentId: paymentId, error: e.message });
        }
    }

    return results;
};
