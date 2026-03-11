exports = async function(amount) {
    const userId = context.user.id;

    if (!userId) {
        throw new Error("User not authenticated.");
    }

    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");
    const returnUrl = context.values.get("MINI_APP_URL"); // Base URL of mini app to return to after payment

    if (!shopId || !secretKey) {
        throw new Error("Server configuration error: Yookassa credentials missing.");
    }

    if (amount < 50 || amount > 50000) {
        throw new Error("Amount must be between 50 and 50000 RUB.");
    }

    const uuidv4 = () => {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    };

    const idempotenceKey = uuidv4();
    const description = `Пополнение баланса на ${amount} ₽`;

    // Fetch user email or provide a default for receipt
    const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
    const user = await usersCollection.findOne({ _id: userId });
    const email = (user && user.email) ? user.email : "no-email@example.com";

    const payload = {
        amount: {
            value: `${amount}.00`,
            currency: "RUB"
        },
        confirmation: {
            type: "redirect",
            return_url: returnUrl || "https://t.me/vpni50_bot"
        },
        capture: true,
        description: description,
        metadata: {
            user_id: userId,
            payment_type: "balance_topup"
        },
        receipt: {
            customer: {
                email: email
            },
            items: [
                {
                    description: description.substring(0, 128),
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
        headers: {
            "Idempotence-Key": [idempotenceKey],
            "Content-Type": ["application/json"]
        },
        authUrl: `https://${shopId}:${secretKey}@api.yookassa.ru`, // Workaround since context.http.post might need basic auth encoded differently
        // Using explicit Authorization header
        // Basic auth: base64(shopId:secretKey)
    });

    // The context.http.post `authUrl` trick is not standard, let's just use the Authorization header explicitly:
    const base64Auth = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

    const properResponse = await context.http.post({
        url: "https://api.yookassa.ru/v3/payments",
        headers: {
            "Idempotence-Key": [idempotenceKey],
            "Content-Type": ["application/json"],
            "Authorization": [`Basic ${base64Auth}`]
        },
        body: payload,
        encodeBodyAsJSON: true
    });

    if (properResponse.statusCode !== 200) {
        throw new Error(`Yookassa API error: ${properResponse.body.text()}`);
    }

    const paymentData = JSON.parse(properResponse.body.text());

    // Save payment to DB
    const pad = (n) => n < 10 ? '0' + n : n;
    const now = new Date();
    const issueDateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

    const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");

    await paymentsCollection.insertOne({
        _id: paymentData.id,
        user_id: userId,
        amount: amount,
        status: 'pending',
        method: 'yookassa_smart',
        timestamp: issueDateStr,
        type: 'balance_topup'
    });

    return {
        paymentId: paymentData.id,
        confirmationUrl: paymentData.confirmation.confirmation_url
    };
};
