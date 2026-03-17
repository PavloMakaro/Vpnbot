exports = async function(amount) {
    const userId = context.user.identities[0].id;
    if (!userId) {
        return { success: false, error: "User ID not found in context." };
    }

    // Yookassa details
    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!shopId || !secretKey) {
        return { success: false, error: "Payment gateway configuration missing." };
    }

    // Auth for Yookassa
    const authString = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

    const paymentData = {
        amount: {
            value: `${amount}.00`,
            currency: "RUB"
        },
        confirmation: {
            type: "redirect",
            return_url: "https://t.me/vpni50_bot" // Placeholder bot link, should match legacy
        },
        capture: true,
        description: `Пополнение баланса на ${amount} ₽`,
        metadata: {
            user_id: userId,
            payment_type: "balance_topup"
        }
    };

    // Generate simple idempotency key
    const key = (Math.random() * 100000000000).toString(36) + Date.now().toString(36);

    try {
        const response = await context.http.post({
            url: "https://api.yookassa.ru/v3/payments",
            headers: {
                "Authorization": [`Basic ${authString}`],
                "Idempotence-Key": [key],
                "Content-Type": ["application/json"]
            },
            body: JSON.stringify(paymentData)
        });

        const responseBody = JSON.parse(response.body.text());

        if (responseBody.type === "error") {
            return { success: false, error: responseBody.description };
        }

        // Save pending payment to DB
        const cluster = context.services.get("mongodb-atlas");
        const db = cluster.db("vpn_bot");
        const paymentsCol = db.collection("payments");

        await paymentsCol.insertOne({
            _id: responseBody.id,
            user_id: userId,
            amount: amount,
            status: 'pending',
            method: 'yookassa_smart',
            timestamp: new Date().toISOString().slice(0, 19).replace('T', ' '),
            type: 'balance_topup'
        });

        return {
            success: true,
            payment_id: responseBody.id,
            confirmation_url: responseBody.confirmation.confirmation_url
        };

    } catch (err) {
        return { success: false, error: err.message };
    }
};
