exports = async function(amount, returnUrl) {
    const userId = context.user.identities[0].id;
    if (!userId) {
        throw new Error("User not authenticated.");
    }

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const usersCol = db.collection("users");
    const paymentsCol = db.collection("payments");

    const user = await usersCol.findOne({ telegram_id: userId });
    if (!user) {
        throw new Error("User profile not found.");
    }

    // Yookassa integration implemented within the Atlas backend functions
    const yookassaShopId = context.values.get("YOOKASSA_SHOP_ID");
    const yookassaSecretKey = context.values.get("YOOKASSA_SECRET_KEY");

    const idempotencyKey = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);

    const payload = {
        amount: {
            value: amount.toFixed(2),
            currency: "RUB"
        },
        confirmation: {
            type: "redirect",
            return_url: returnUrl || "https://t.me/vpn_bot"
        },
        capture: true,
        description: `Balance topup for ${amount} RUB`,
        metadata: {
            user_id: userId,
            payment_type: "balance_topup"
        },
        receipt: {
            customer: {
                email: user.email || "no-email@example.com"
            },
            items: [
                {
                    description: `Balance topup for ${amount} RUB`,
                    quantity: "1.00",
                    amount: {
                        value: amount.toFixed(2),
                        currency: "RUB"
                    },
                    vat_code: 1
                }
            ]
        }
    };

    const response = await context.http.post({
        url: "https://api.yookassa.ru/v3/payments",
        headers: {
            "Content-Type": ["application/json"],
            "Authorization": [`Basic ${Buffer.from(yookassaShopId + ":" + yookassaSecretKey).toString("base64")}`],
            "Idempotence-Key": [idempotencyKey]
        },
        body: JSON.stringify(payload)
    });

    if (response.statusCode >= 200 && response.statusCode < 300) {
        const payment = JSON.parse(response.body.text());

        await paymentsCol.insertOne({
            payment_id: payment.id,
            user_id: userId,
            amount: amount,
            status: "pending",
            method: "yookassa_smart",
            timestamp: new Date(),
            type: "balance_topup"
        });

        return payment;
    } else {
        throw new Error(`Failed to create payment: ${response.body.text()}`);
    }
};