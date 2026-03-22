exports = async function(amount, description, returnUrl) {
    const telegramId = context.user.identities[0].id.toString();
    if (!telegramId) {
        throw new Error("Unauthorized");
    }

    // Ensure amount is an integer
    const amountInt = parseInt(amount, 10);
    if (isNaN(amountInt) || amountInt <= 0) {
        throw new Error("Invalid amount");
    }

    // Yookassa Integration
    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");
    if (!shopId || !secretKey) {
        throw new Error("Yookassa credentials not configured.");
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCollection = db.collection("users");
    const user = await usersCollection.findOne({ _id: telegramId });

    const email = user && user.email ? user.email : "no-email@example.com";

    // Generate an idempotency key (UUID)
    const idempotenceKey = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);

    const payload = {
        amount: {
            value: `${amountInt}.00`,
            currency: "RUB"
        },
        confirmation: {
            type: "redirect",
            return_url: returnUrl || "https://t.me/vpni50_bot"
        },
        capture: true,
        description: description || "Пополнение баланса",
        metadata: {
            user_id: telegramId,
            payment_type: "balance_topup"
        },
        receipt: {
            customer: {
                email: email
            },
            items: [
                {
                    description: (description || "Пополнение баланса").substring(0, 128),
                    quantity: "1.00",
                    amount: {
                        value: `${amountInt}.00`,
                        currency: "RUB"
                    },
                    vat_code: 1
                }
            ]
        }
    };

    const response = await context.http.post({
        url: "https://api.yookassa.ru/v3/payments",
        body: payload,
        encodeBodyAsJSON: true,
        headers: {
            "Content-Type": ["application/json"],
            "Idempotence-Key": [idempotenceKey],
            "Authorization": ["Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64")]
        }
    });

    if (response.statusCode >= 400) {
        throw new Error(`Yookassa API error: ${response.body.text()}`);
    }

    const payment = JSON.parse(response.body.text());

    // Store pending payment in database
    const paymentsCollection = db.collection("payments");
    await paymentsCollection.insertOne({
        _id: payment.id,
        user_id: telegramId,
        amount: amountInt,
        status: "pending",
        method: "yookassa_smart",
        timestamp: new Date(),
        type: "balance_topup"
    });

    return payment.confirmation.confirmation_url;
};
