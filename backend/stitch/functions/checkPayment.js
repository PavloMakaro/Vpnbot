exports = async function(paymentId) {
    const yooShopId = context.values.get("YOOKASSA_SHOP_ID");
    const yooSecretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!yooShopId || !yooSecretKey) {
        return { success: false, message: "Payment gateway not configured" };
    }

    const auth = Buffer.from(`${yooShopId}:${yooSecretKey}`).toString('base64');

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const payment = await db.collection("payments").findOne({ payment_id: paymentId });

    if (!payment) {
        return { success: false, message: "Payment not found" };
    }

    if (payment.status !== "pending") {
        return { success: true, status: payment.status };
    }

    const headers = {
        "Authorization": [`Basic ${auth}`]
    };

    const response = await context.http.get({
        url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
        headers: headers
    });

    if (response.statusCode >= 200 && response.statusCode < 300) {
        const body = JSON.parse(response.body.text());

        if (body.status === "succeeded") {
            await db.collection("payments").updateOne({ payment_id: paymentId }, { $set: { status: "confirmed" } });
            await db.collection("users").updateOne({ _id: payment.user_id }, { $inc: { balance: payment.amount } });
            return { success: true, status: "confirmed" };
        } else if (body.status === "canceled") {
            await db.collection("payments").updateOne({ payment_id: paymentId }, { $set: { status: "canceled" } });
            return { success: true, status: "canceled" };
        } else {
            return { success: true, status: "pending" };
        }
    } else {
        return { success: false, message: "Failed to check payment status" };
    }
};
