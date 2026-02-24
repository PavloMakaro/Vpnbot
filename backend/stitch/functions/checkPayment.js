exports = async function(paymentId) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("Unauthorized");
  }

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const paymentsCollection = db.collection("payments");
  const usersCollection = db.collection("users");

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Payment service not configured");
  }

  // 1. Check local status first
  const localPayment = await paymentsCollection.findOne({ _id: paymentId });
  if (!localPayment) {
    throw new Error("Payment not found");
  }

  if (localPayment.status === "succeeded") {
    return { status: "succeeded", already_processed: true };
  }

  // 2. Call Yookassa API
  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": [`Basic ${Buffer.from(shopId + ":" + secretKey).toString("base64")}`]
    }
  });

  if (response.statusCode !== 200) {
    throw new Error("Failed to check payment status with provider");
  }

  const paymentInfo = JSON.parse(response.body.text());

  // 3. Update payment status
  if (paymentInfo.status === "succeeded") {
    // Atomically update status to prevent double processing
    const updateResult = await paymentsCollection.updateOne(
      { _id: paymentId, status: { $ne: "succeeded" } },
      {
        $set: {
          status: "succeeded",
          captured_at: new Date(),
          provider_data: paymentInfo
        }
      }
    );

    if (updateResult.modifiedCount === 1) {
      // 4. Credit user balance
      const amount = parseFloat(paymentInfo.amount.value);
      await usersCollection.updateOne(
        { _id: localPayment.user_id },
        { $inc: { balance: amount } }
      );
      return { status: "succeeded", new_balance: true };
    } else {
      // Another process (webhook?) might have updated it
      return { status: "succeeded", already_processed: true };
    }
  } else if (paymentInfo.status === "canceled") {
      await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "canceled" } }
      );
      return { status: "canceled" };
  }

  return { status: paymentInfo.status };
};
