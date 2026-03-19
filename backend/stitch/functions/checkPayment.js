exports = async function(paymentId) {
    const userId = context.user.identities[0].id;

    if (!userId) {
        return { success: false, error: "User ID not found in context" };
    }

    const mongodb = context.services.get("mongodb-atlas");
    const paymentsColl = mongodb.db("vpn_bot").collection("payments");
    const usersColl = mongodb.db("vpn_bot").collection("users");

    const payment = await paymentsColl.findOne({ _id: paymentId, user_id: userId });

    if (!payment) {
        return { success: false, error: "Платеж не найден" };
    }

    if (payment.status === 'confirmed') {
        return { success: true, status: 'confirmed' };
    }

    // Yookassa Integration setup
    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    // In local dev/test without credentials, simulate success
    if (!shopId || !secretKey) {
        console.warn("YOOKASSA credentials missing. Simulating successful check.");
        await paymentsColl.updateOne({ _id: paymentId }, { $set: { status: 'confirmed' } });
        await usersColl.updateOne({ _id: userId }, { $inc: { balance: payment.amount } });
        return { success: true, status: 'confirmed' };
    }

    const authString = Buffer.from(`${shopId}:${secretKey}`).toString("base64");

    try {
        const response = await context.http.get({
            url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
            headers: {
                "Authorization": [`Basic ${authString}`]
            }
        });

        if (response.statusCode >= 200 && response.statusCode < 300) {
            const yookassaResponse = JSON.parse(response.body.text());

            if (yookassaResponse.status === 'succeeded') {
                // Payment successful - update balance
                await usersColl.updateOne(
                    { _id: userId },
                    { $inc: { balance: payment.amount } }
                );

                // Update payment status
                await paymentsColl.updateOne(
                    { _id: paymentId },
                    { $set: { status: 'confirmed' } }
                );

                return { success: true, status: 'confirmed' };
            } else if (yookassaResponse.status === 'canceled') {
                await paymentsColl.updateOne(
                    { _id: paymentId },
                    { $set: { status: 'canceled' } }
                );
                return { success: true, status: 'canceled' };
            } else {
                return { success: true, status: 'pending' };
            }
        } else {
            console.error("Yookassa Error:", response.body.text());
            return { success: false, error: "Ошибка API Yookassa" };
        }
    } catch (e) {
        console.error("Yookassa check error:", e);
        return { success: false, error: "Ошибка проверки платежа" };
    }
};