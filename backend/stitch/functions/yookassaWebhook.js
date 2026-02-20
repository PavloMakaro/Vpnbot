// Start of Selection
exports = async function({ query, headers, body }, response) {
    const payload = JSON.parse(body.text());
    const event = payload.event;
    const object = payload.object;

    if (event === "payment.succeeded") {
        const payments = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
        const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

        const paymentId = object.id;
        const amount = parseFloat(object.amount.value);
        const userId = object.metadata.user_id; // We stored this in metadata

        // Check if already processed
        const existingPayment = await payments.findOne({ _id: paymentId });

        if (existingPayment && existingPayment.status !== "succeeded") {
            // Update Payment Status
            await payments.updateOne(
                { _id: paymentId },
                { $set: { status: "succeeded", succeeded_at: new Date() } }
            );

            // Update User Balance
            // Note: If metadata user_id is missing, use existingPayment.user_id
            const targetUserId = userId || existingPayment.user_id;

            if (targetUserId) {
                 await users.updateOne(
                    { _id: targetUserId },
                    { $inc: { balance: amount } }
                );
                console.log(`Payment ${paymentId} succeeded. User ${targetUserId} balance updated.`);
            } else {
                console.error(`Payment ${paymentId} succeeded but no user_id found.`);
            }
        } else {
            console.log(`Payment ${paymentId} already processed or not found.`);
        }
    }

    response.setStatusCode(200);
    response.setBody(JSON.stringify({ status: "ok" }));
};
