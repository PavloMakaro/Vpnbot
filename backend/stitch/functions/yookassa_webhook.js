exports = async function(payload, response) {
  // This function should be configured as an HTTPS Endpoint
  // payload.body contains the webhook data

  const body = EJSON.parse(payload.body.text());
  const event = body.event;
  const object = body.object;

  if (event === "payment.succeeded") {
    const paymentId = object.id;
    const userId = object.metadata.user_id;

    // SECURITY: Verify payment status with YooKassa API directly
    const shopId = context.values.get("yookassa_shop_id");
    const secretKey = context.values.get("yookassa_secret_key");

    if (!shopId || !secretKey) {
      console.error("YooKassa credentials not configured");
      return;
    }

    try {
      const apiResponse = await context.http.get({
        url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
        headers: {
          "Authorization": "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64"),
          "Content-Type": "application/json"
        }
      });

      if (apiResponse.statusCode !== 200) {
        console.error("Failed to verify payment with YooKassa API", apiResponse.body.text());
        return;
      }

      const paymentData = JSON.parse(apiResponse.body.text());

      if (paymentData.status !== "succeeded") {
        console.warn(`Payment ${paymentId} status is ${paymentData.status}, expected succeeded`);
        return;
      }

      const amount = parseFloat(paymentData.amount.value);

      const mongodb = context.services.get("mongodb-atlas");
      const db = mongodb.db("vpn_bot");
      const paymentsCollection = db.collection("payments");
      const usersCollection = db.collection("users");

      // Check if payment already processed
      const paymentDoc = await paymentsCollection.findOne({ _id: paymentId });
      if (paymentDoc && paymentDoc.status === "succeeded") {
        return; // Already processed
      }

      // Update payment status
      await paymentsCollection.updateOne(
        { _id: paymentId },
        { $set: { status: "succeeded", updated_at: new Date() } },
        { upsert: true }
      );

      // Update user balance
      await usersCollection.updateOne(
        { _id: userId },
        { $inc: { balance: amount } }
      );

      console.log(`Payment ${paymentId} verified and succeeded for user ${userId}. Amount: ${amount}`);

    } catch (err) {
      console.error("Error processing webhook:", err);
    }
  }
};
