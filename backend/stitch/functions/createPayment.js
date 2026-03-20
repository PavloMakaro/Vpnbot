exports = async function(amount, description) {
    const userId = context.user.identities[0].id;
    if (!userId) {
        return { error: "User not authenticated" };
    }

    if (!amount || amount < 50 || amount > 50000) {
        return { error: "Invalid amount. Must be between 50 and 50000." };
    }

    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!shopId || !secretKey) {
        console.error("Yookassa configuration missing");
        return { error: "Payment gateway configuration error." };
    }

    // Generate idempotency key instead of randomUUID (which context.functions might not support)
    const idempotencyKey = "pay_" + Date.now() + "_" + Math.floor(Math.random() * 100000);

    const authHeader = "Basic " + Buffer.from(shopId + ":" + secretKey).toString("base64");

    const paymentData = {
        amount: {
            value: amount.toFixed(2),
            currency: "RUB"
        },
        confirmation: {
            type: "redirect",
            return_url: "https://t.me/vpni50_bot" // Using the generic bot link
        },
        capture: true,
        description: description || `Topup balance for ${amount} RUB`,
        metadata: {
            user_id: userId,
            payment_type: "balance_topup"
        }
    };

    try {
        const response = await context.http.post({
            url: "https://api.yookassa.ru/v3/payments",
            headers: {
                "Authorization": [authHeader],
                "Idempotence-Key": [idempotencyKey],
                "Content-Type": ["application/json"]
            },
            body: JSON.stringify(paymentData)
        });

        if (response.statusCode >= 400) {
            console.error("Yookassa error: ", response.body.text());
            return { error: "Failed to create payment in Yookassa." };
        }

        const yookassaPayment = EJSON.parse(response.body.text());

        // Save pending payment record using Yookassa ID as primary key
        // to match legacy architecture behavior and avoid primary key issues
        const db = context.services.get("mongodb-atlas").db("vpn_bot");
        await db.collection("payments").insertOne({
            _id: yookassaPayment.id,
            user_id: userId,
            amount: amount,
            status: "pending",
            method: "yookassa_smart",
            timestamp: new Date(),
            type: "balance_topup"
        });

        return {
            payment_id: yookassaPayment.id,
            confirmation_url: yookassaPayment.confirmation.confirmation_url
        };

    } catch (e) {
        console.error("Error creating payment:", e);
        return { error: "Internal payment creation error." };
    }
};