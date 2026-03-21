exports = async function() {
    const userId = context.user.identities[0].id;
    if (!userId) {
        throw new Error("User not authenticated.");
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCol = db.collection("payments");
    const usersCol = db.collection("users");

    const pendingPayments = await paymentsCol.find({ user_id: userId, status: "pending", method: "yookassa_smart" }).toArray();

    const yookassaShopId = context.values.get("YOOKASSA_SHOP_ID");
    const yookassaSecretKey = context.values.get("YOOKASSA_SECRET_KEY");

    const results = [];

    for (const paymentRecord of pendingPayments) {
        const response = await context.http.get({
            url: `https://api.yookassa.ru/v3/payments/${paymentRecord.payment_id}`,
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
                    { payment_id: paymentRecord.payment_id },
                    { $set: { status: "confirmed" } }
                );

                results.push({ payment_id: paymentRecord.payment_id, status: "confirmed" });
            } else if (paymentData.status === "canceled") {
                await paymentsCol.updateOne(
                    { payment_id: paymentRecord.payment_id },
                    { $set: { status: "canceled" } }
                );

                results.push({ payment_id: paymentRecord.payment_id, status: "canceled" });
            } else {
                results.push({ payment_id: paymentRecord.payment_id, status: "pending" });
            }
        } else {
            console.error(`Failed to check payment ${paymentRecord.payment_id}: ${response.body.text()}`);
        }
    }

    return results;
};