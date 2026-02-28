exports = async function(paymentId) {
    const userId = context.user.id;
    if (!userId) {
        throw new Error("User is not authenticated.");
    }

    if (!paymentId) {
        throw new Error("Missing payment ID.");
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot_db");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    // Fetch payment from DB
    const paymentDoc = await paymentsCollection.findOne({ _id: paymentId, user_id: userId });

    if (!paymentDoc) {
        return { status: "not_found", message: "Платеж не найден." };
    }

    if (paymentDoc.status === "succeeded" || paymentDoc.status === "confirmed") {
        return { status: "already_processed", message: "Платеж уже обработан." };
    }

    if (paymentDoc.status === "canceled") {
        return { status: "canceled", message: "Платеж был отменен." };
    }

    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!shopId || !secretKey) {
        throw new Error("Yookassa credentials are not configured.");
    }

    const credentials = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

    // Call Yookassa to check status
    const response = await context.http.get({
        url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
        headers: {
            "Authorization": [`Basic ${credentials}`]
        }
    });

    if (response.statusCode !== 200) {
        console.error("Yookassa Check Error:", response.body.text());
        return { status: "error", message: "Ошибка при проверке статуса платежа." };
    }

    const paymentData = JSON.parse(response.body.text());

    // Update payment record in database
    await paymentsCollection.updateOne(
        { _id: paymentId },
        { $set: { status: paymentData.status } }
    );

    if (paymentData.status === "succeeded") {
        // Add to user balance
        const amount = parseFloat(paymentData.amount.value);
        await usersCollection.updateOne(
            { _id: userId },
            { $inc: { balance: amount } }
        );

        return { status: "succeeded", message: `✅ Баланс успешно пополнен на ${amount} ₽!` };
    } else if (paymentData.status === "canceled") {
         return { status: "canceled", message: "Платеж был отменен." };
    } else {
        return { status: "pending", message: "Платеж еще не подтвержден." };
    }
};