exports = async function() {
    const userId = context.user.id;
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    try {
        const pendingPayments = await paymentsCollection.find({
            user_id: userId,
            status: "pending",
            method: "yookassa_smart"
        }).toArray();

        if (pendingPayments.length === 0) {
            return { message: "No pending payments found" };
        }

        const shopId = context.values.get("YOOKASSA_SHOP_ID");
        const secretKey = context.values.get("YOOKASSA_SECRET_KEY");
        const authHeader = "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64");

        let checkedCount = 0;
        let confirmedCount = 0;
        let totalAmountAdded = 0;

        for (const payment of pendingPayments) {
            checkedCount++;

            const url = `https://api.yookassa.ru/v3/payments/${payment._id}`;
            const response = await context.http.get({
                url: url,
                headers: {
                    "Authorization": [authHeader]
                }
            });

            const responseData = JSON.parse(response.body.text());

            if (responseData.type === "error") {
                console.error(`Error checking payment ${payment._id}:`, responseData);
                continue;
            }

            if (responseData.status === "succeeded") {
                // Update payment status
                const updateResult = await paymentsCollection.updateOne(
                    { _id: payment._id, status: "pending" },
                    { $set: { status: "confirmed", confirmed_at: new Date() } }
                );

                if (updateResult.modifiedCount > 0) {
                    // Add amount to user's balance
                    await usersCollection.updateOne(
                        { _id: userId },
                        { $inc: { balance: payment.amount } }
                    );
                    confirmedCount++;
                    totalAmountAdded += payment.amount;
                }
            } else if (responseData.status === "canceled") {
                await paymentsCollection.updateOne(
                    { _id: payment._id },
                    { $set: { status: "canceled", updated_at: new Date() } }
                );
            }
        }

        return {
            checked: checkedCount,
            confirmed: confirmedCount,
            total_added: totalAmountAdded,
            message: `Checked ${checkedCount} payments, confirmed ${confirmedCount}`
        };

    } catch (e) {
        console.error("Check pending payments error:", e);
        return { error: "Failed to check pending payments" };
    }
};