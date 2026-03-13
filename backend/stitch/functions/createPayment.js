exports = async function(amount, returnUrl) {
    const yooShopId = context.values.get("YOOKASSA_SHOP_ID");
    const yooSecretKey = context.values.get("YOOKASSA_SECRET_KEY");
    const userId = context.user.id;

    if (!yooShopId || !yooSecretKey) {
        return { success: false, message: "Payment gateway not configured" };
    }

    const auth = Buffer.from(`${yooShopId}:${yooSecretKey}`).toString('base64');

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const user = await db.collection("users").findOne({ _id: userId });

    const idempotencyKey = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments").aggregate([{$limit:1}])._id || Math.random().toString();
    const headers = {
        "Authorization": [`Basic ${auth}`],
        "Idempotence-Key": [new Date().getTime().toString()],
        "Content-Type": ["application/json"]
    };

    const payload = {
        amount: {
            value: `${amount}.00`,
            currency: "RUB"
        },
        confirmation: {
            type: "redirect",
            return_url: returnUrl || "https://t.me/your_bot"
        },
        capture: true,
        description: `Balance topup for ${amount} RUB`,
        metadata: {
            user_id: userId,
            payment_type: "balance_topup"
        },
        receipt: {
            customer: {
                email: user?.email || "no-email@example.com"
            },
            items: [
                {
                    description: "Balance topup",
                    quantity: "1.00",
                    amount: {
                        value: `${amount}.00`,
                        currency: "RUB"
                    },
                    vat_code: 1
                }
            ]
        }
    };

    const response = await context.http.post({
        url: "https://api.yookassa.ru/v3/payments",
        headers: headers,
        body: JSON.stringify(payload)
    });

    if (response.statusCode >= 200 && response.statusCode < 300) {
        const body = JSON.parse(response.body.text());

        await db.collection("payments").insertOne({
            payment_id: body.id,
            user_id: userId,
            amount: amount,
            status: "pending",
            method: "yookassa_smart",
            timestamp: new Date(),
            type: "balance_topup"
        });

        return { success: true, paymentId: body.id, confirmationUrl: body.confirmation.confirmation_url };
    } else {
        return { success: false, message: "Failed to create payment" };
    }
};
