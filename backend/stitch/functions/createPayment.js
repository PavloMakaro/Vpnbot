exports = async function(amount) {
    const userId = context.user.identities[0].id;
    if (!userId) {
        return { success: false, error: "User ID not found in context" };
    }

    if (amount < 50 || amount > 50000) {
        return { success: false, error: "Invalid amount" };
    }

    const mongodb = context.services.get("mongodb-atlas");
    const usersColl = mongodb.db("vpn_bot").collection("users");
    const paymentsColl = mongodb.db("vpn_bot").collection("payments");

    const user = await usersColl.findOne({ _id: userId });
    if (!user) {
        return { success: false, error: "User not found" };
    }

    // Yookassa Integration setup
    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    // In local dev/test without credentials, simulate success
    if (!shopId || !secretKey) {
        console.warn("YOOKASSA credentials missing. Generating mock payment.");
        const mockPaymentId = "mock_payment_" + new Date().getTime();
        await paymentsColl.insertOne({
            _id: mockPaymentId,
            user_id: userId,
            amount: amount,
            status: "pending",
            method: "yookassa_smart",
            timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
            type: "balance_topup"
        });
        return {
            success: true,
            confirmation_url: `https://example.com/mock-pay?id=${mockPaymentId}`
        };
    }

    // Call YooKassa API via context.http
    const authString = Buffer.from(`${shopId}:${secretKey}`).toString("base64");
    const idempotenceKey = new Date().getTime().toString() + "_" + Math.floor(Math.random() * 10000).toString();

    try {
        const response = await context.http.post({
            url: "https://api.yookassa.ru/v3/payments",
            headers: {
                "Authorization": [`Basic ${authString}`],
                "Idempotence-Key": [idempotenceKey],
                "Content-Type": ["application/json"]
            },
            body: JSON.stringify({
                amount: {
                    value: `${amount}.00`,
                    currency: "RUB"
                },
                confirmation: {
                    type: "redirect",
                    return_url: "https://t.me/vpn_bot" // Update with real return URL
                },
                capture: true,
                description: `Пополнение баланса на ${amount} ₽`,
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
                            description: `Пополнение баланса на ${amount} ₽`,
                            quantity: "1.00",
                            amount: {
                                value: `${amount}.00`,
                                currency: "RUB"
                            },
                            vat_code: 1
                        }
                    ]
                }
            })
        });

        if (response.statusCode >= 200 && response.statusCode < 300) {
            const bodyStr = response.body.text();
            const yookassaResponse = JSON.parse(bodyStr);

            // Save to database
            await paymentsColl.insertOne({
                _id: yookassaResponse.id,
                user_id: userId,
                amount: amount,
                status: "pending",
                method: "yookassa_smart",
                timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
                type: "balance_topup"
            });

            return {
                success: true,
                confirmation_url: yookassaResponse.confirmation.confirmation_url
            };
        } else {
            console.error("Yookassa Error:", response.body.text());
            return { success: false, error: "Ошибка API Yookassa" };
        }
    } catch (e) {
        console.error("Yookassa Error:", e);
        return { success: false, error: "Ошибка создания платежа" };
    }
};