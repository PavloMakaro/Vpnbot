exports = async function(amount) {
    const userId = context.user.id;
    if (!userId) {
        throw new Error("User is not authenticated.");
    }

    if (!amount || amount < 50) {
        throw new Error("Минимальная сумма пополнения 50 ₽.");
    }

    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!shopId || !secretKey) {
        throw new Error("Yookassa credentials are not configured.");
    }

    const credentials = Buffer.from(`${shopId}:${secretKey}`).toString('base64');
    const paymentIdStr = new context.services.get("mongodb-atlas").bson.ObjectId().toString();

    // Call Yookassa API via context.http
    const response = await context.http.post({
        url: "https://api.yookassa.ru/v3/payments",
        headers: {
            "Authorization": [`Basic ${credentials}`],
            "Idempotence-Key": [paymentIdStr],
            "Content-Type": ["application/json"]
        },
        body: JSON.stringify({
            amount: {
                value: `${amount}.00`,
                currency: "RUB"
            },
            confirmation: {
                type: "redirect",
                return_url: "https://t.me/vpni50_bot" // Redirect to bot after payment
            },
            capture: true,
            description: `Пополнение баланса на ${amount} ₽`,
            metadata: {
                user_id: userId,
                payment_type: "balance_topup"
            }
        })
    });

    if (response.statusCode !== 200) {
        console.error("Yookassa Error:", response.body.text());
        throw new Error("Failed to create payment with Yookassa.");
    }

    const paymentData = JSON.parse(response.body.text());

    // Save payment intent in the DB
    const db = context.services.get("mongodb-atlas").db("vpn_bot_db");
    const paymentsCollection = db.collection("payments");

    await paymentsCollection.insertOne({
        _id: paymentData.id,
        user_id: userId,
        amount: amount,
        status: paymentData.status,
        method: "yookassa_smart",
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        timestamp_date: new Date(),
        type: "balance_topup"
    });

    return {
        payment_id: paymentData.id,
        confirmation_url: paymentData.confirmation.confirmation_url
    };
};