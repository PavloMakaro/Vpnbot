exports = async function(amount, description, returnUrl) {
    const userId = context.user.id;
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    try {
        const userProfile = await usersCollection.findOne({ _id: userId });
        if (!userProfile) {
            return { error: "User not found" };
        }

        const shopId = context.values.get("YOOKASSA_SHOP_ID");
        const secretKey = context.values.get("YOOKASSA_SECRET_KEY");
        const idempotencyKey = require("crypto").randomBytes(16).toString("hex");

        const url = "https://api.yookassa.ru/v3/payments";
        const authHeader = "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64");

        const paymentData = {
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
                    email: userProfile.email || "no-email@example.com"
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
            url: url,
            headers: {
                "Authorization": [authHeader],
                "Idempotence-Key": [idempotencyKey],
                "Content-Type": ["application/json"]
            },
            body: JSON.stringify(paymentData)
        });

        const responseData = JSON.parse(response.body.text());

        if (responseData.type === "error") {
            console.error("Yookassa error:", responseData);
            return { error: responseData.description || "Payment creation failed" };
        }

        // Save pending payment to DB
        await paymentsCollection.insertOne({
            _id: responseData.id,
            user_id: userId,
            amount: amount,
            status: "pending",
            method: "yookassa_smart",
            timestamp: new Date(),
            type: "balance_topup",
            payment_id: responseData.id
        });

        return {
            paymentId: responseData.id,
            confirmationUrl: responseData.confirmation.confirmation_url
        };

    } catch (e) {
        console.error("Create payment error:", e);
        return { error: "Failed to create payment" };
    }
};