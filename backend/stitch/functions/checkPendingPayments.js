exports = async function() {
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    // Fetch all pending Yookassa payments
    const pendingPayments = await paymentsCollection.find({
        status: "pending",
        method: "yookassa_smart"
    }).toArray();

    if (pendingPayments.length === 0) {
        return { message: "No pending payments to check." };
    }

    const shopId = context.values.get("YOOKASSA_SHOP_ID");
    const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

    if (!shopId || !secretKey) {
        console.error("Yookassa configuration missing");
        return { error: "Payment gateway configuration error." };
    }

    const authHeader = "Basic " + Buffer.from(shopId + ":" + secretKey).toString("base64");

    let processedCount = 0;
    let failedCount = 0;

    for (const payment of pendingPayments) {
        try {
            const response = await context.http.get({
                url: `https://api.yookassa.ru/v3/payments/${payment._id}`,
                headers: {
                    "Authorization": [authHeader]
                }
            });

            if (response.statusCode >= 400) {
                console.error(`Yookassa error for payment ${payment._id}: `, response.body.text());
                failedCount++;
                continue;
            }

            const yookassaPayment = EJSON.parse(response.body.text());
            const status = yookassaPayment.status;

            if (status === 'succeeded') {
                const updateResult = await paymentsCollection.updateOne(
                    { _id: payment._id, status: "pending" },
                    { $set: { status: "confirmed" } }
                );

                if (updateResult.modifiedCount > 0) {
                    await usersCollection.updateOne(
                        { _id: payment.user_id },
                        { $inc: { balance: payment.amount } }
                    );
                    processedCount++;
                }
            } else if (status === 'canceled') {
                await paymentsCollection.updateOne(
                    { _id: payment._id, status: "pending" },
                    { $set: { status: "canceled" } }
                );
                processedCount++;
            }
        } catch (e) {
            console.error(`Error checking pending payment ${payment._id}:`, e);
            failedCount++;
        }
    }

    return {
        message: `Checked ${pendingPayments.length} payments. Processed ${processedCount}, Failed ${failedCount}.`
    };
};